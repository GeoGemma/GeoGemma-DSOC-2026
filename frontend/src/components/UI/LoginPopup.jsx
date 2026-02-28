import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import '../../styles/loginPopup.css';

const LoginPopup = ({ onClose }) => {
  const { signInWithGoogle, error } = useAuth();

  const handleSignIn = async () => {
    const user = await signInWithGoogle();
    if (user) {
      onClose();
    }
  };

  return (
    <div className="login-popup-overlay">
      <div className="login-popup">
        <div className="login-popup-header">
          <h2>Sign In Required</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        <div className="login-popup-content">
          <p>Please sign in to use GeoGemma's features.</p>
          {error && <div className="error-message">{error}</div>}
          <button 
            className="google-signin-button" 
            onClick={handleSignIn}
          >
            <img 
              src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" 
              alt="Google logo" 
            />
            Sign in with Google
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPopup; 