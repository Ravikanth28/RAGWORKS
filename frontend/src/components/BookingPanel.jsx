import { useState } from 'react'

export default function BookingPanel({ selectedSlot, slotMeta, onBook }) {
  const [duration, setDuration] = useState(1)
  const [booking, setBooking] = useState(false)

  const rate = slotMeta?.ratePerHour || 20
  const cost = duration * rate

  // Calculate start and end times
  const startTime = new Date();
  const endTime = new Date(startTime.getTime() + duration * 60 * 60 * 1000);
  
  const formatTime = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const handleBook = async () => {
    if (!selectedSlot || booking) return
    setBooking(true)
    await onBook(duration, selectedSlot)
    setBooking(false)
  }

  if (!selectedSlot) return null

  return (
    <div className="booking-section">
      <div className="booking-form">
        <h3>🎫 Book Slot — {selectedSlot}</h3>
        <div className="booking-form-grid">
          <div className="form-group">
            <label className="label" htmlFor="slot-display">Selected Slot</label>
            <input
              id="slot-display"
              className="input"
              value={selectedSlot}
              readOnly
            />
          </div>
          <div className="form-group">
            <label className="label" htmlFor="duration-input">Duration (Hours)</label>
            <select
              id="duration-input"
              className="select"
              value={duration}
              onChange={e => setDuration(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5, 6, 8, 10, 12, 24].map(h => (
                <option key={h} value={h}>{h} {h === 1 ? 'hour' : 'hours'}</option>
              ))}
            </select>
          </div>
          <button
            id="book-slot-btn"
            className="btn btn-success"
            onClick={handleBook}
            disabled={booking}
          >
            {booking ? '⏳ Booking...' : '🅿️ Book Slot'}
          </button>
        </div>
        <div className="timings-preview">
          <div className="timing-detail">
            <span className="timing-label">Start Time</span>
            <span className="timing-value">{formatTime(startTime)}</span>
          </div>
          <div className="timing-divider">→</div>
          <div className="timing-detail">
            <span className="timing-label">End Time</span>
            <span className="timing-value">{formatTime(endTime)}</span>
          </div>
        </div>
        <div className="cost-preview">
          <span className="cost-label">Estimated Cost ({duration}h × ₹{rate})</span>
          <span className="cost-value">₹{cost}</span>
        </div>
      </div>
    </div>
  )
}
