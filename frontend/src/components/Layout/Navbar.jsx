import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Navbar.css';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isAdmin = user?.role === 'admin';

  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          CodeTrainer
        </Link>

        <div className="nav-menu">
          <Link to="/exercises" className="nav-link">
            Exercices
          </Link>

          {/* Section Admin — visible uniquement pour les admins connectés */}
          {isAdmin && (
            <Link to="/admin" className="nav-link nav-link-admin">
              ⚙ Admin
            </Link>
          )}

          {user ? (
            <>
              <Link to="/profile" className="nav-link">
                {user.username || user.email}
              </Link>
              <button onClick={handleLogout} className="nav-link btn-logout">
                Déconnexion
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="nav-link">
                Connexion
              </Link>
              <Link to="/register" className="nav-link btn-register">
                Inscription
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
