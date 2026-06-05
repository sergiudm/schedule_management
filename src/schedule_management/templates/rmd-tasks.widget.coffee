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

  .prio-high
    color: #ff6b6b
  .prio-mid
    color: #ffd93d
  .prio-low
    color: #6bc5ff

  .overdue
    color: #ff6b6b
    font-weight: 600

  .postponed
    color: #888
    font-style: italic

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
    prioNum = parseInt(task.priority.match(/\((\d+)\)/)?[1] or '0')
    prioClass = if prioNum >= 8 then 'prio-high' else if prioNum >= 5 then 'prio-mid' else 'prio-low'

    descClass = 'task-desc'
    if task.desc.indexOf('⏳') >= 0
      descClass += ' overdue'
    else if task.desc.indexOf('💤') >= 0
      descClass += ' postponed'

    html += """
      <div class="task-row">
        <span class="task-id">#{task.id}</span>
        <span class="task-priority #{prioClass}">#{task.priority}</span>
        <span class="#{descClass}">#{task.desc}</span>
      </div>
    """

  if total
    html += "<div class='footer'>#{total} tasks</div>"

  return html
