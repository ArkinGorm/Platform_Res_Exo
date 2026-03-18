import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Layout/Navbar';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import ExerciseList from './components/Exercises/ExerciseList';
import ExerciseDetail from './components/Exercises/ExerciseDetail';
import './App.css';

// Route protégée
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) return <div>Chargement...</div>;
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  return children;
};

function AppContent() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route 
          path="/exercises" 
          element={
            <ProtectedRoute>
              <ExerciseList />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/exercises/:id" 
          element={
            <ProtectedRoute>
              <ExerciseDetail />
            </ProtectedRoute>
          } 
        />
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