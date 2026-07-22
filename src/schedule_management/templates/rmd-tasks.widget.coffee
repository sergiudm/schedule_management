command: "{{RMD_PATH}} ls 2>&1"

refreshFrequency: {{REFRESH_FREQUENCY}}

style: """
  top: 50%
  left: 50%
  transform: translate(-50%, -50%)
  width: 420px
  font-family: 'SF Mono', 'Menlo', 'Monaco', monospace
  font-size: 12px
  color: #e0e0e0
  background: rgba(20, 20, 30, 0.85)
  -webkit-backdrop-filter: blur(16px)
  border-radius: 12px
  border: 1px solid rgba(255, 255, 255, 0.08)
  padding: 16px 18px
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4)

  .header
    font-size: 14px
    font-weight: 600
    color: #7ecfff
    margin-bottom: 12px
    letter-spacing: 0.5px

  .task-row
    display: flex
    align-items: center
    padding: 4px 0
    gap: 10px

  .task-id
    color: #666
    width: 24px
    text-align: right
    flex-shrink: 0

  .task-priority
    width: 110px
    flex-shrink: 0
    font-size: 11px

  .task-desc
    flex: 1
    word-break: break-word
    overflow-wrap: break-word

  .type-1
    color: #ff6b6b   // red
  .type-2
    color: #51cf66   // green
  .type-3
    color: #6bc5ff   // blue
  .type-4
    color: #ffd93d   // yellow
  .type-5
    color: #cc5de8   // magenta
  .type-6
    color: #15aabf   // cyan
  .type-7
    color: #e0e0e0   // white
  .type-default
    color: #e0e0e0

  .overdue
    color: #ff6b6b
    font-weight: 600

  .postponed
    color: #888
    font-style: italic

  .delete-btn
    background: transparent
    border: none
    color: #666
    cursor: pointer
    font-size: 11px
    padding: 2px 6px
    border-radius: 4px
    transition: all 0.2s ease
    flex-shrink: 0

  .delete-btn:hover
    color: #ff6b6b
    background: rgba(255, 107, 107, 0.15)

  .delete-btn.confirming
    color: #ff6b6b
    background: rgba(255, 107, 107, 0.25)
    font-weight: 600

  .delete-btn.executing
    color: #888
    cursor: wait

  .footer
    margin-top: 10px
    text-align: right
    font-size: 10px
    color: #555

  .empty
    text-align: center
    color: #888
    padding: 20px
"""

render: (output) ->
  lines = output.split('\n')

  stripAnsi = (str) ->
    str.replace(/\x1b\[[0-9;]*m/g, '').replace(/\u001b\[[0-9;]*m/g, '')

  tasks = []
  for line in lines
    stripped = stripAnsi(line)
    if stripped.indexOf('│') >= 0 and stripped.indexOf('ID') < 0 and stripped.indexOf('───') < 0 and stripped.indexOf('Priority') < 0
      parts = stripped.split('│').filter (p) -> p.trim().length > 0
      if parts.length >= 3
        id = parts[0].trim()
        priority = parts[1].trim()
        desc = parts[2].trim()
        if id.match(/^\d+$/)
          tasks.push { id, priority, desc }

  totalMatch = output.match(/Total tasks:\s*(\d+)/)
  total = if totalMatch then totalMatch[1] else null

  if tasks.length == 0
    return '<div class="empty">📋 No tasks</div>'

  html = '<div class="header">📋 Tasks</div>'

  for task in tasks
    typeMatch = task.desc.match(/\u2060(\d+)/)
    typeId = if typeMatch then typeMatch[1] else 'default'
    prioClass = "type-#{typeId}"
    cleanDesc = task.desc.replace(/\u2060\d+/, '')

    descClass = 'task-desc'
    if cleanDesc.indexOf('⏳') >= 0
      descClass += ' overdue'
    else if cleanDesc.indexOf('💤') >= 0
      descClass += ' postponed'

    html += """
      <div class="task-row">
        <span class="task-id">#{task.id}</span>
        <span class="task-priority #{prioClass}">#{task.priority}</span>
        <span class="#{descClass}">#{cleanDesc}</span>
        <button class="delete-btn" data-id="#{task.id}" title="Delete task">✕</button>
      </div>
    """

  if total
    html += "<div class='footer'>#{total} tasks</div>"

  return html

afterRender: (domEl) ->
  domEl.addEventListener 'click', (e) =>
    btn = e.target.closest('.delete-btn')
    return unless btn

    taskId = btn.getAttribute('data-id')
    return unless taskId

    if btn.classList.contains('confirming')
      if btn._resetTimer
        clearTimeout(btn._resetTimer)
        btn._resetTimer = null
      btn.classList.remove('confirming')
      btn.classList.add('executing')
      btn.innerText = '...'
      @run "{{RMD_PATH}} rm #{taskId}", (err, stdout) =>
        @refresh()
    else
      btn.classList.add('confirming')
      btn.innerText = 'Confirm?'
      btn._resetTimer = setTimeout (->
        btn.classList.remove('confirming')
        btn.innerText = '✕'
        btn._resetTimer = null
      ), 3000

