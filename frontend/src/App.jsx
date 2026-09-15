import React, { useState } from 'react';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';

export default function App() {
  const [intakeOpen, setIntakeOpen] = useState(false);
  return intakeOpen ? <Dashboard /> : <LandingPage onStart={() => setIntakeOpen(true)} />;
}
