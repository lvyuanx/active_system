const form = document.querySelector("#launch-form");
const apiBaseUrl = document.querySelector("#api-base-url");
const token = document.querySelector("#token");
const displayList = document.querySelector("#display-list");
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
  displayList.querySelectorAll("input").forEach((input) => {
    input.disabled = loading;
  });
};
const selectedDisplayIds = () => Array.from(
  displayList.querySelectorAll("input[name=\"display-id\"]:checked"),
).map((input) => Number(input.value));
const loadDisplays = async () => {
  try {
    const displays = await window.danmakuDesktop.listDisplays();
    if (displays.length === 0) throw new Error("没有可用的投屏显示器");
    displayList.replaceChildren(...displays.map((display) => {
      const option = document.createElement("label");
      option.className = "display-option";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.name = "display-id";
      checkbox.value = String(display.id);
      checkbox.checked = display.isPrimary || displays.length === 1;
      const copy = document.createElement("span");
      copy.className = "display-option-copy";
      copy.textContent = `${display.label} - ${display.width} x ${display.height}${display.isPrimary ? "（主屏）" : ""}`;
      option.append(checkbox, copy);
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
  const displayIds = selectedDisplayIds();
  if (displayIds.length === 0) {
    setStatus("请至少选择一个投屏显示器", "error");
    setLoading(false);
    return;
  }
  try {
    await window.danmakuDesktop.start({
      apiBaseUrl: apiBaseUrl.value,
      token: token.value,
      displayIds,
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
