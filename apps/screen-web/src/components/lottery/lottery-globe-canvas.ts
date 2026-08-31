export function drawGlobeGuide(
  target: CanvasRenderingContext2D,
  width: number,
  height: number,
  radius: number,
): void {
  const centerX = width / 2;
  const centerY = height / 2;
  const glow = target.createRadialGradient(centerX, centerY, radius * 0.25, centerX, centerY, radius * 1.1);
  glow.addColorStop(0, "rgba(76, 224, 195, 0.12)");
  glow.addColorStop(0.7, "rgba(112, 92, 255, 0.08)");
  glow.addColorStop(1, "rgba(112, 92, 255, 0)");
  target.fillStyle = glow;
  target.beginPath();
  target.arc(centerX, centerY, radius * 1.14, 0, Math.PI * 2);
  target.fill();
  target.strokeStyle = "rgba(119, 115, 239, 0.22)";
  target.lineWidth = 1;
  target.beginPath();
  target.arc(centerX, centerY, radius, 0, Math.PI * 2);
  target.stroke();
  target.beginPath();
  target.ellipse(centerX, centerY, radius, radius * 0.36, 0, 0, Math.PI * 2);
  target.stroke();
  target.beginPath();
  target.ellipse(centerX, centerY, radius * 0.36, radius, 0, 0, Math.PI * 2);
  target.stroke();
}

export function renderGlobeGuide(
  guideCanvas: HTMLCanvasElement,
  width: number,
  height: number,
  pixelRatio: number,
  radius: number,
): void {
  guideCanvas.width = Math.max(1, Math.floor(width * pixelRatio));
  guideCanvas.height = Math.max(1, Math.floor(height * pixelRatio));
  const guideContext = guideCanvas.getContext("2d");
  if (!guideContext) return;
  guideContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  guideContext.clearRect(0, 0, width, height);
  drawGlobeGuide(guideContext, width, height, radius);
}
