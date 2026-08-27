const form = document.querySelector("#launch-form");
const apiBaseUrl = document.querySelector("#api-base-url");
const token = document.querySelector("#token");
const displayId = document.querySelector("#display-id");
const status = document.querySelector("#status");
const startButton = document.querySelector("#start-button");
const resumeButton = document.querySelector("#resume-button");
const stopButton = document.querySelector("#stop-button");

const setStatus = (message, type = "") => {
  status.textContent = message;
  status.dataset.type = type;
};
const setLoading = (loading) => {
  startButton.disabled = loading;
  resumeButton.disabled = loading;
  stopButton.disabled = loading;
};
const loadDisplays = async () => {
  try {
    const displays = await window.danmakuDesktop.listDisplays();
    displayId.replaceChildren(...displays.map((display) => {
      const option = document.createElement("option");
      option.value = String(display.id);
      option.textContent = `${display.label} - ${display.width} x ${display.height}${display.isPrimary ? "（主屏）" : ""}`;
      return option;
    }));
    setStatus("");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "无法读取显示器", "error");
  }
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);
  setStatus("正在验证 token…");
  try {
    await window.danmakuDesktop.start({
      apiBaseUrl: apiBaseUrl.value,
      token: token.value,
      displayId: Number(displayId.value),
    });
    setStatus("弹幕已启动", "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "启动失败", "error");
  } finally {
    setLoading(false);
  }
});
resumeButton.addEventListener("click", async () => {
  setLoading(true);
  try {
    await window.danmakuDesktop.resume();
    setStatus("弹幕已恢复", "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "无法恢复弹幕", "error");
  } finally {
    setLoading(false);
  }
});
stopButton.addEventListener("click", async () => {
  setLoading(true);
  try {
    await window.danmakuDesktop.stop();
    setStatus("弹幕已停止");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "无法停止弹幕", "error");
  } finally {
    setLoading(false);
  }
});

loadDisplays();
