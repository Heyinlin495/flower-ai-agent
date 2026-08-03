export default function (component) {
  const { parentElement, setTriggerValue, data } = component;
  const root = parentElement.querySelector('#sessionSidebarRoot');
  // 防御：组件被卸载/节点 detached 时直接返回（避免 React 移除冲突）
  if (!root || !root.isConnected) return;

  const sessions = (data && data.sessions) || [];
  const currentSid = (data && data.current_sid) || '';

  // 用 replaceChildren 重建，避免逐条 removeChild 在 rerun 时与 React 竞争
  const frag = document.createDocumentFragment();

  // 空态提示
  if (!sessions.length) {
    const empty = document.createElement('div');
    empty.className = 'session-empty';
    empty.textContent = '暂无会话，点击上方"新建会话"开始';
    frag.appendChild(empty);
  }

  sessions.forEach(function (s) {
    const item = document.createElement('div');
    item.className = 'session-item' + (s.id === currentSid ? ' active' : '');
    item.dataset.sid = s.id;

    // 会话标题（点击切换）
    const titleBtn = document.createElement('button');
    titleBtn.type = 'button';
    titleBtn.className = 'session-title';
    titleBtn.textContent = s.title;
    titleBtn.title = s.ts + ' — ' + s.title;
    titleBtn.addEventListener('click', function () {
      setTriggerValue('select', { value: s.id });
    });

    // 删除按钮（hover 显示）
    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'session-del';
    delBtn.textContent = '✕';
    delBtn.title = '删除「' + s.title + '」';
    delBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      setTriggerValue('delete', { value: s.id });
    });

    // 时间徽标
    const tsBadge = document.createElement('span');
    tsBadge.className = 'session-ts';
    tsBadge.textContent = s.ts;

    item.appendChild(titleBtn);
    item.appendChild(tsBadge);
    item.appendChild(delBtn);
    frag.appendChild(item);
  });

  // 一次性替换（原子操作，避免逐个 append 造成中间态）
  root.replaceChildren(frag);
}
