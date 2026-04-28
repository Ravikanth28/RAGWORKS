import { useState, useEffect, useRef } from 'react'

export default function Timer({ expiresAt, totalDuration, onExpire }) {
  const [remaining, setRemaining] = useState(0)
  const totalSeconds = totalDuration * 3600
  const expiredFired = useRef(false)

  useEffect(() => {
    expiredFired.current = false   // reset if expiresAt changes (new booking)

    const update = () => {
      const now = new Date()
      const end = new Date(expiresAt)
      const diff = Math.max(0, Math.floor((end - now) / 1000))
      setRemaining(diff)

      if (diff <= 0 && !expiredFired.current) {
        expiredFired.current = true
        // Small delay so the backend threading.Timer has time to release the slot
        if (onExpire) setTimeout(onExpire, 1500)
      }
    }

    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [expiresAt, onExpire])

  const hours = Math.floor(remaining / 3600)
  const minutes = Math.floor((remaining % 3600) / 60)
  const seconds = remaining % 60
  const percent = totalSeconds > 0 ? (remaining / totalSeconds) * 100 : 0

  const timerClass = remaining < 300 ? 'critical' : remaining < 900 ? 'warning' : ''

  return (
    <div className="timer-display">
      <div className="timer-label">Time Remaining</div>
      <div className={`timer-value ${timerClass}`}>
        {String(hours).padStart(2, '0')}:{String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </div>
      <div className="timer-progress">
        <div
          className={`timer-progress-bar ${timerClass}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}
