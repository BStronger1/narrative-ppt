const screens = {
  audience: {src: 'screenshots/audience-settings.jpg', alt: '应用中的听众、知识基础与讲述目标设置', caption: '01 / 真实应用截图：确认听众与沟通目标。'},
  narrative: {src: 'screenshots/narrative-plan.jpg', alt: '应用中的 AI 叙事方案和阶段安排', caption: '02 / 真实应用截图：先审阅全篇叙事方案，再生成大纲。'},
  editor: {src: 'screenshots/live-editor.jpg', alt: '真实模型生成后的编辑器和来源面板', caption: '03 / 真实应用截图：编辑页面，查看材料来源，导出 PPTX。'}
};
const shot = document.getElementById('product-shot');
const caption = document.getElementById('shot-caption');
document.querySelectorAll('[data-screen]').forEach(button => {
  button.addEventListener('click', () => {
    const screen = screens[button.dataset.screen];
    if (!screen) return;
    shot.src = screen.src;
    shot.alt = screen.alt;
    caption.textContent = screen.caption;
    document.querySelectorAll('[data-screen]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  });
});
