export type ScheduledTaskId = number;

export type TaskCallback = () => void;

export type FrameRequest = (callback: (timestamp: number) => void) => number;
export type FrameCancel = (handle: number) => void;

export type TaskSchedulerOptions = {
  requestFrame?: FrameRequest;
  cancelFrame?: FrameCancel;
  now?: () => number;
  frameBudgetMs?: number;
  maxTasksPerFrame?: number;
  onError?: (error: unknown) => void;
};

export type TaskScheduler = {
  scheduleAt: (dueAt: number, callback: TaskCallback) => ScheduledTaskId;
  scheduleAfter: (delayMs: number, callback: TaskCallback) => ScheduledTaskId;
  cancel: (taskId: ScheduledTaskId) => void;
  clear: () => void;
  pendingCount: () => number;
};

type ScheduledTask = {
  id: ScheduledTaskId;
  dueAt: number;
  callback: TaskCallback;
};

const DEFAULT_FRAME_BUDGET_MS = 4;
const DEFAULT_MAX_TASKS_PER_FRAME = 32;

export function createTaskScheduler(options: TaskSchedulerOptions = {}): TaskScheduler {
  const requestFrame = options.requestFrame ?? ((callback) => window.requestAnimationFrame(callback));
  const cancelFrame = options.cancelFrame ?? ((handle) => window.cancelAnimationFrame(handle));
  const now = options.now ?? (() => performance.now());
  const frameBudgetMs = options.frameBudgetMs ?? DEFAULT_FRAME_BUDGET_MS;
  const maxTasksPerFrame = options.maxTasksPerFrame ?? DEFAULT_MAX_TASKS_PER_FRAME;
  const onError = options.onError ?? ((error) => console.error("弹幕调度任务执行失败", error));

  if (
    !Number.isFinite(frameBudgetMs)
    || frameBudgetMs <= 0
    || !Number.isInteger(maxTasksPerFrame)
    || maxTasksPerFrame <= 0
  ) {
    throw new Error("弹幕调度器参数必须大于 0");
  }

  let tasks: ScheduledTask[] = [];
  let frameHandle: number | undefined;
  let nextTaskId = 1;

  const sortTasks = () => {
    tasks.sort((first, second) => first.dueAt - second.dueAt || first.id - second.id);
  };
  const requestNextFrame = () => {
    if (frameHandle !== undefined || tasks.length === 0) return;
    frameHandle = requestFrame(runFrame);
  };
  const stopFrameIfIdle = () => {
    if (tasks.length > 0 || frameHandle === undefined) return;
    cancelFrame(frameHandle);
    frameHandle = undefined;
  };
  const runFrame = (frameTimestamp: number) => {
    frameHandle = undefined;
    const frameStartedAt = Math.max(frameTimestamp, now());
    const frameDeadline = frameStartedAt + frameBudgetMs;
    let executedTasks = 0;

    while (tasks.length > 0 && executedTasks < maxTasksPerFrame) {
      const currentTime = now();
      const task = tasks[0];
      if (task.dueAt > currentTime || currentTime > frameDeadline) break;
      tasks.shift();
      executedTasks += 1;
      try {
        task.callback();
      } catch (error) {
        onError(error);
      }
    }
    requestNextFrame();
  };

  const scheduleAt = (dueAt: number, callback: TaskCallback): ScheduledTaskId => {
    if (!Number.isFinite(dueAt)) throw new Error("弹幕调度任务时间无效");
    const task = { id: nextTaskId++, dueAt, callback };
    tasks.push(task);
    sortTasks();
    requestNextFrame();
    return task.id;
  };
  const scheduleAfter = (delayMs: number, callback: TaskCallback) => {
    if (!Number.isFinite(delayMs)) throw new Error("弹幕调度任务延迟无效");
    return scheduleAt(now() + Math.max(0, delayMs), callback);
  };
  const cancel = (taskId: ScheduledTaskId) => {
    const taskIndex = tasks.findIndex((task) => task.id === taskId);
    if (taskIndex < 0) return;
    tasks.splice(taskIndex, 1);
    stopFrameIfIdle();
  };
  const clear = () => {
    tasks = [];
    if (frameHandle !== undefined) {
      cancelFrame(frameHandle);
      frameHandle = undefined;
    }
  };

  return {
    scheduleAt,
    scheduleAfter,
    cancel,
    clear,
    pendingCount: () => tasks.length,
  };
}
