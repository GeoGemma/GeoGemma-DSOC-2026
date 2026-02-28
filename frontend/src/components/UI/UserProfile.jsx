// src/components/UI/UserProfile.jsx
import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
// We'll keep the import but won't use the style directly
// import '../../styles/userProfile.css';

// This component is being replaced by ProfileMenu.jsx
// It's kept to avoid breaking changes, but will return null
const UserProfile = () => {
  const { currentUser } = useAuth();

  // No longer render this component
  return null;
};

export default UserProfile;