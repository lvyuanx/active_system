import { computed, onBeforeUnmount, onMounted, ref, watch, type InjectionKey, type Ref } from "vue";

const KEYBOARD_OPEN_DELTA = 150;
const KEYBOARD_CLOSE_DELTA = 100;
const KEYBOARD_FOCUS_FALLBACK_DELAY = 300;
const KEYBOARD_LOCK_CLASS = "activity-keyboard-lock";

export const activityKeyboardVisibleKey: InjectionKey<Ref<boolean>> = Symbol("activity-keyboard-visible");

type ViewportSnapshot = {
  height: number;
  offsetTop: number;
  scale: number;
};

const readOrientation = () => (window.innerWidth >= window.innerHeight ? "landscape" : "portrait");

const isTextEntryElement = (target: EventTarget | null): target is HTMLElement => {
  if (!(target instanceof HTMLElement)) return false;
  return target instanceof HTMLInputElement
    || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement
    || target.isContentEditable;
};

const readViewport = (): ViewportSnapshot => {
  const viewport = window.visualViewport;
  return {
    height: Math.max(0, viewport?.height ?? window.innerHeight),
    offsetTop: Math.max(0, viewport?.offsetTop ?? 0),
    scale: viewport?.scale ?? 1,
  };
};

export const useKeyboardViewport = (active: Ref<boolean>) => {
  const keyboardVisible = ref(false);
  const viewportHeight = ref(0);
  const viewportOffsetTop = ref(0);
  let baselineHeight = 0;
  let baselineOrientation = "";
  let textInputFocused = false;
  let keyboardHeightObserved = false;
  let animationFrame = 0;
  let focusResetTimer = 0;
  let keyboardFallbackTimer = 0;
  let documentScrollRestoreFrame = 0;

  const resetBaseline = (height: number) => {
    baselineHeight = height;
    baselineOrientation = readOrientation();
  };

  const updateViewport = () => {
    animationFrame = 0;
    if (!active.value) {
      keyboardVisible.value = false;
      return;
    }

    const current = readViewport();
    viewportHeight.value = current.height;
    viewportOffsetTop.value = current.offsetTop;

    const orientation = readOrientation();
    if (!baselineHeight || orientation !== baselineOrientation) {
      resetBaseline(current.height);
      keyboardVisible.value = false;
      keyboardHeightObserved = false;
      return;
    }

    // Pinch zoom changes visualViewport dimensions without opening the keyboard.
    if (Math.abs(current.scale - 1) > 0.01) return;

    if (!textInputFocused && !keyboardVisible.value) baselineHeight = current.height;

    const heightReduction = baselineHeight - current.height;
    if (heightReduction >= KEYBOARD_OPEN_DELTA) keyboardHeightObserved = true;
    if (!keyboardVisible.value && textInputFocused && heightReduction >= KEYBOARD_OPEN_DELTA) {
      keyboardVisible.value = true;
    } else if (
      keyboardVisible.value
      && heightReduction <= KEYBOARD_CLOSE_DELTA
      && (!textInputFocused || keyboardHeightObserved)
    ) {
      keyboardVisible.value = false;
    }
  };

  const scheduleViewportUpdate = () => {
    if (animationFrame) return;
    animationFrame = window.requestAnimationFrame(updateViewport);
  };

  const setDocumentKeyboardLock = (locked: boolean) => {
    if (typeof document === "undefined") return;
    document.documentElement.classList.toggle(KEYBOARD_LOCK_CLASS, locked);
  };

  const restoreDocumentScroll = () => {
    if (typeof document === "undefined") return;
    const restore = () => {
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    };
    restore();
    if (documentScrollRestoreFrame) window.cancelAnimationFrame(documentScrollRestoreFrame);
    documentScrollRestoreFrame = window.requestAnimationFrame(() => {
      documentScrollRestoreFrame = 0;
      restore();
    });
  };

  const restoreViewportAfterKeyboard = () => {
    if (baselineHeight > 0) {
      viewportHeight.value = Math.max(baselineHeight, readViewport().height);
      viewportOffsetTop.value = 0;
    }
    restoreDocumentScroll();
  };

  const isTouchDevice = () => navigator.maxTouchPoints > 0 || "ontouchstart" in window;

  const clearKeyboardFallback = () => {
    window.clearTimeout(keyboardFallbackTimer);
    keyboardFallbackTimer = 0;
  };

  const scheduleKeyboardFallback = () => {
    clearKeyboardFallback();
    if (!isTouchDevice()) return;
    keyboardFallbackTimer = window.setTimeout(() => {
      keyboardFallbackTimer = 0;
      if (active.value && textInputFocused && !keyboardVisible.value) {
        // Some embedded iOS WebViews do not emit a visualViewport resize for the keyboard.
        keyboardVisible.value = true;
      }
    }, KEYBOARD_FOCUS_FALLBACK_DELAY);
  };

  const handleFocusIn = (event: FocusEvent) => {
    if (active.value && isTextEntryElement(event.target)) {
      textInputFocused = true;
      scheduleViewportUpdate();
      scheduleKeyboardFallback();
    }
  };

  const handleFocusOut = (event: FocusEvent) => {
    if (!isTextEntryElement(event.target)) return;
    window.clearTimeout(focusResetTimer);
    focusResetTimer = window.setTimeout(() => {
      textInputFocused = isTextEntryElement(document.activeElement);
      if (!textInputFocused) {
        clearKeyboardFallback();
        restoreDocumentScroll();
      }
      scheduleViewportUpdate();
    }, 0);
  };

  const handleViewportChange = () => scheduleViewportUpdate();

  const activate = () => {
    const current = readViewport();
    resetBaseline(current.height);
    viewportHeight.value = current.height;
    viewportOffsetTop.value = current.offsetTop;
    textInputFocused = isTextEntryElement(document.activeElement);
    keyboardVisible.value = false;
    keyboardHeightObserved = false;
    clearKeyboardFallback();
    scheduleViewportUpdate();
  };

  const deactivate = () => {
    keyboardVisible.value = false;
    viewportHeight.value = 0;
    viewportOffsetTop.value = 0;
    baselineHeight = 0;
    baselineOrientation = "";
    textInputFocused = false;
    keyboardHeightObserved = false;
    window.clearTimeout(focusResetTimer);
    clearKeyboardFallback();
    if (animationFrame) window.cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    if (documentScrollRestoreFrame) window.cancelAnimationFrame(documentScrollRestoreFrame);
    documentScrollRestoreFrame = 0;
  };

  const viewportStyle = computed<Record<string, string>>(() => ({
    "--activity-viewport-height": viewportHeight.value > 0 ? `${viewportHeight.value}px` : "100dvh",
    "--activity-viewport-offset-top": `${viewportOffsetTop.value}px`,
  }));

  onMounted(() => {
    setDocumentKeyboardLock(false);
    document.addEventListener("focusin", handleFocusIn);
    document.addEventListener("focusout", handleFocusOut);
    window.addEventListener("resize", handleViewportChange);
    window.visualViewport?.addEventListener("resize", handleViewportChange);
    window.visualViewport?.addEventListener("scroll", handleViewportChange);
    if (active.value) activate();
  });

  watch(active, (enabled) => {
    if (enabled) activate();
    else deactivate();
  });

  watch(
    keyboardVisible,
    (visible) => {
      setDocumentKeyboardLock(visible);
      if (!visible) restoreViewportAfterKeyboard();
    },
    { flush: "sync" },
  );

  onBeforeUnmount(() => {
    document.removeEventListener("focusin", handleFocusIn);
    document.removeEventListener("focusout", handleFocusOut);
    window.removeEventListener("resize", handleViewportChange);
    window.visualViewport?.removeEventListener("resize", handleViewportChange);
    window.visualViewport?.removeEventListener("scroll", handleViewportChange);
    deactivate();
    setDocumentKeyboardLock(false);
  });

  return { keyboardVisible, viewportStyle };
};
