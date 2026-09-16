document.addEventListener('DOMContentLoaded', function () {
  const DURATION = 5000; // 5 секунд

  function setupToast(toast) {
    if (toast.dataset.initialized) return;
    toast.dataset.initialized = 'true';

    const closeBtn = toast.querySelector('.message-close');
    let startTime = Date.now();
    let remaining = DURATION;
    let timerId = null;

    function dismiss() {
      clearTimeout(timerId);
      toast.classList.add('slide-out');
      setTimeout(() => {
        toast.remove();
        const container = document.getElementById('messagesContainer');
        if (container && container.children.length === 0) {
          container.remove();
        }
      }, 300);
    }

    function startTimer() {
      startTime = Date.now();
      timerId = setTimeout(dismiss, remaining);
    }

    function pauseTimer() {
      clearTimeout(timerId);
      remaining -= (Date.now() - startTime);
      if (remaining < 0) remaining = 0;
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dismiss();
      });
    }

    toast.addEventListener('mouseenter', pauseTimer);
    toast.addEventListener('mouseleave', () => {
      if (remaining > 0) startTimer();
    });

    startTimer();
  }

  document.querySelectorAll('.message-item').forEach(setupToast);
});