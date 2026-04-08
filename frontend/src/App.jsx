import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Layout/Navbar';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import ExerciseList from './components/Exercises/ExerciseList';
import ExerciseDetail from './components/Exercises/ExerciseDetail';
import AdminDashboard from './components/Admin/AdminDashboard';
import ExerciseForm from './components/Admin/ExerciseForm';
import GenerateAI from './components/Admin/GenerateAI';
import './App.css';

// ── Route protégée (authentification) ──────────────────────────
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div>Chargement...</div>;
  if (!user)   return <Navigate to="/login" />;
  return children;
};

// ── Route admin uniquement ──────────────────────────────────────
const AdminRoute = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div>Chargement...</div>;
  if (!user)              return <Navigate to="/login" />;
  if (user.role !== 'admin') return <Navigate to="/exercises" />;
  return children;
};

function AppContent() {
  return (
    <>
      <Navbar />
      <Routes>
        {/* Auth */}
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Participant */}
        <Route path="/exercises" element={
          <ProtectedRoute><ExerciseList /></ProtectedRoute>
        }/>
        <Route path="/exercises/:id" element={
          <ProtectedRoute><ExerciseDetail /></ProtectedRoute>
        }/>

        {/* Admin */}
        <Route path="/admin" element={
          <AdminRoute><AdminDashboard /></AdminRoute>
        }/>
        <Route path="/admin/exercises/create" element={
          <AdminRoute><ExerciseForm /></AdminRoute>
        }/>
        <Route path="/admin/exercises/:id/edit" element={
          <AdminRoute><ExerciseForm /></AdminRoute>
        }/>
        <Route path="/admin/generate" element={
          <AdminRoute><GenerateAI /></AdminRoute>
        } />

        <Route path="/" element={<Navigate to="/exercises" />} />
      </Routes>
    </>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <Toaster position="top-right" />
        <AppContent />
      </AuthProvider>
    </Router>
  );
}

export default App;
