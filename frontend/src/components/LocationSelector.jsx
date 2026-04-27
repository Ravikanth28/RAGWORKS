export default function LocationSelector({ locations, selectedLocation, onSelect }) {
  return (
    <div className="location-panel">
      <h2>📍 Locations</h2>
      <div className="location-list">
        {locations.map(loc => (
          <div
            key={loc.id}
            id={`location-${loc.id}`}
            className={`location-card ${selectedLocation === loc.id ? 'active' : ''}`}
            onClick={() => onSelect(loc.id)}
          >
            <div className="location-name">{loc.name}</div>
            <div className="location-address">{loc.address}</div>
            <div className="location-meta">
              <span className={`location-slots ${loc.availableSlots > 0 ? 'has-slots' : 'full'}`}>
                {loc.availableSlots > 0
                  ? `${loc.availableSlots}/${loc.totalSlots} available`
                  : 'Full'}
              </span>
              <span className="location-rate">₹{loc.ratePerHour}/hr</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
