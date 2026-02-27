import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import './App.css';

const App = () => {
  return (
    <Router>
      <div className="app">
        <nav className="sidebar">
          <h1>Dhan Algo Terminal</h1>
          <Link to="/">Dashboard</Link>
          <Link to="/config">Config</Link>
          <Link to="/strategies">Strategies</Link>
          <Link to="/control">Controls</Link>
        </nav>
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/config" element={<Config />} />
            <Route path="/strategies" element={<Strategies />} />
            <Route path="/control" element={<Control />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

const Dashboard = () => <div><h2>Dashboard</h2><p>System Status & Live P&L</p></div>;
const Config = () => <div><h2>Configuration</h2><p>Dhan API Settings</p></div>;
const Strategies = () => <div><h2>Strategies</h2><p>Manage Trading Strategies</p></div>;
const Control = () => <div><h2>Controls</h2><p>Kill Switch & Risk Settings</p></div>;

export default App;
