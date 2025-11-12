import React, { useState } from 'react';
import './styles/PlannerObservation.scss';

const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const hours = Array.from({ length: 24 }, (_, i) => i); // 8 AM to 8 PM

// Helper to get dates for current week
const getWeekDates = () => {
  const today = new Date();
  const weekStart = new Date(today.setDate(today.getDate() - today.getDay() + 1)); // Monday
  return daysOfWeek.map((_, i) => {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    return d;
  });
};

const PlannerObservation = () => {
  const [events, setEvents] = useState({}); // { 'YYYY-MM-DD': { hour: [event1, event2] } }
  const [modal, setModal] = useState({ open: false, day: null, hour: null, text: '' });

  const weekDates = getWeekDates();

  const openModal = (day, hour) => {
    setModal({ open: true, day, hour, text: '' });
  };

  const closeModal = () => setModal({ open: false, day: null, hour: null, text: '' });

  const handleSaveEvent = () => {
    setEvents(prev => {
      const dayEvents = prev[modal.day] || {};
      const hourEvents = dayEvents[modal.hour] || [];
      return {
        ...prev,
        [modal.day]: {
          ...dayEvents,
          [modal.hour]: [...hourEvents, modal.text]
        }
      };
    });
    closeModal();
  };

  const handleDeleteEvent = (day, hour, index) => {
    setEvents(prev => {
      const dayEvents = { ...prev[day] };
      dayEvents[hour] = dayEvents[hour].filter((_, i) => i !== index);
      return { ...prev, [day]: dayEvents };
    });
  };

  return (
    <div className="planner">
      <h2>Planner of the observation</h2>
      <div className="header-row">
        <div className="time-column"></div>
        {weekDates.map((date, idx) => (
          <div key={idx} className="day-column">
            {daysOfWeek[idx]} <br /> {date.toLocaleDateString()}
          </div>
        ))}
      </div>

      {hours.map(hour => (
        <div key={hour} className="hour-row">
          <div className="time-column">{hour}:00</div>
          {weekDates.map((date, idx) => {
            const dayKey = date.toISOString().split('T')[0];
            const hourEvents = events[dayKey]?.[hour] || [];
            return (
              <div key={idx} className="day-cell" onClick={() => openModal(dayKey, hour)}>
                {hourEvents.map((evt, i) => (
                  <div key={i} className="event">
                    {evt} <span className="delete" onClick={(e) => { e.stopPropagation(); handleDeleteEvent(dayKey, hour, i); }}>×</span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      ))}

      {modal.open && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Add Event</h3>
            <input
              type="text"
              value={modal.text}
              onChange={(e) => setModal({ ...modal, text: e.target.value })}
              placeholder="Event description"
            />
            <div className="modal-buttons">
              <button onClick={handleSaveEvent}>Save</button>
              <button onClick={closeModal}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlannerObservation;
