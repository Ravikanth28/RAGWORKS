import { useCallback } from 'react'
import Timer from './Timer'

export default function ActiveBookings({ bookings, onRelease, onRefresh, onExpire }) {
  const handleRelease = useCallback(async (bookingId) => {
    if (window.confirm('Are you sure you want to release this slot?')) {
      await onRelease(bookingId)
    }
  }, [onRelease])

  if (!bookings || bookings.length === 0) return null

  return (
    <div className="bookings-section">
      <h2>
        🎯 Active Bookings
        <span className="badge badge-cyan">{bookings.length}</span>
      </h2>
      <div className="bookings-grid">
        {bookings.map(b => (
          <div key={b.booking_id} className="booking-card" id={`booking-${b.booking_id}`}>
            <div className="booking-card-header">
              <span className="booking-id">#{b.booking_id}</span>
              <span className="badge badge-green">● Active</span>
            </div>
            <div className="booking-details">
              <div className="booking-detail">
                <span className="booking-detail-label">Location</span>
                <span className="booking-detail-value">{b.location_name}</span>
              </div>
              <div className="booking-detail">
                <span className="booking-detail-label">Slot</span>
                <span className="booking-detail-value">{b.slot_id}</span>
              </div>
              <div className="booking-detail">
                <span className="booking-detail-label">Duration</span>
                <span className="booking-detail-value">{b.duration}h</span>
              </div>
              <div className="booking-detail">
                <span className="booking-detail-label">Cost</span>
                <span className="booking-detail-value">{b.currency}{b.cost}</span>
              </div>
            </div>
            <Timer
              expiresAt={b.expires_at}
              totalDuration={b.duration}
              onExpire={() => onExpire ? onExpire(b.slot_id) : onRefresh()}
            />
            <button
              id={`release-${b.booking_id}`}
              className="btn btn-danger"
              style={{ width: '100%' }}
              onClick={() => handleRelease(b.booking_id)}
            >
              🔓 Release Slot
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
