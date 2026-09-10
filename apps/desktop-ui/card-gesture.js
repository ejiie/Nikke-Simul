// A hold opens details; releasing it must never also select the character.
let cancelActivePress = () => {};
window.addEventListener('blur', () => cancelActivePress());
window.addEventListener('scroll', () => cancelActivePress(), { capture: true, passive: true });
export function bindCardGesture(card, { isSelecting, select, detail }) {
  let timer, start, held = false, cancelled = false;
  const clear = () => { clearTimeout(timer); timer = null; };
  const cancel = () => { if (start) cancelled = true; clear(); };
  card.addEventListener('pointerdown', e => {
    if (!isSelecting() || e.button !== 0 || !e.isPrimary) return;
    cancelActivePress(); cancelActivePress = cancel;
    clear(); held = false; cancelled = false;
    start = { x: e.clientX, y: e.clientY, id: e.pointerId };
    card.setPointerCapture(e.pointerId);
    timer = setTimeout(() => {
      clear();
      if (!card.isConnected || !isSelecting() || document.hidden) return;
      held = true; detail();
    }, 1000);
  });
  card.addEventListener('pointermove', e => {
    if (start && Math.hypot(e.clientX - start.x, e.clientY - start.y) > 10) cancel();
  });
  card.addEventListener('pointerup', () => { clear(); start = null; });
  card.addEventListener('pointercancel', () => { cancel(); start = null; });
  card.addEventListener('lostpointercapture', cancel);
  card.addEventListener('contextmenu', e => { if (isSelecting()) { e.preventDefault(); cancel(); } });
  card.addEventListener('dragstart', e => { e.preventDefault(); cancel(); });
  card.addEventListener('keydown', e => {
    // Keyboard users can open details without a pointer hold.
    if (isSelecting() && e.key === 'Enter' && e.altKey) { e.preventDefault(); detail(); }
  });
  card.addEventListener('click', e => {
    if (held || cancelled) { e.preventDefault(); held = false; cancelled = false; return; }
    if (isSelecting()) select(); else detail();
  });
}
