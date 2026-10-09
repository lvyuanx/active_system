import { afterEach, describe, expect, it, vi } from "vitest";
import { ReconnectingSocket } from "../src/services/socket";

type MockTask = {
  onOpen: (callback: () => void) => void;
  onMessage: (callback: (event: { data: string }) => void) => void;
  onClose: (callback: () => void) => void;
  onError: (callback: (error: { errMsg: string }) => void) => void;
  send: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
  open?: () => void;
};

const globalWithWx = globalThis as typeof globalThis & { wx?: typeof wx };
const originalWx = globalWithWx.wx;

const createTask = (): MockTask => {
  const task = {
    onOpen: vi.fn((callback: () => void) => { task.open = callback; }),
    onMessage: vi.fn(),
    onClose: vi.fn(),
    onError: vi.fn(),
    send: vi.fn(),
    close: vi.fn(),
    open: undefined as (() => void) | undefined,
  } as MockTask;
  return task;
};

afterEach(() => {
  globalWithWx.wx = originalWx;
  vi.restoreAllMocks();
});

describe("ReconnectingSocket", () => {
  it("连接尚未打开时停止不会调用 close", () => {
    const task = createTask();
    globalWithWx.wx = { connectSocket: vi.fn(() => task) } as unknown as typeof wx;
    const socket = new ReconnectingSocket("wss://example.test/ws");

    socket.start();
    socket.stop();

    expect(task.close).not.toHaveBeenCalled();
  });

  it("已打开的连接会安全关闭并提供失败回调", () => {
    const task = createTask();
    globalWithWx.wx = { connectSocket: vi.fn(() => task) } as unknown as typeof wx;
    const socket = new ReconnectingSocket("wss://example.test/ws");

    socket.start();
    task.open?.();
    socket.stop();

    expect(task.close).toHaveBeenCalledWith(expect.objectContaining({ fail: expect.any(Function) }));
  });
});
