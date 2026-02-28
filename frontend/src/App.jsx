// src/App.jsx
import { useState, useEffect } from 'react';
import { MapProvider } from './contexts/MapContext';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout/Layout';
import AppMap from './components/Map/AppMap';
import Sidebar from './components/Sidebar/Sidebar';
import RightSidebar from './components/Sidebar/RightSidebar';
import PromptForm from './components/UI/PromptForm';
import Notification from './components/UI/Notification.jsx';
import StatusIndicator from './components/UI/StatusIndicator.jsx';
import FloatingDrawingTools from './components/Map/DrawingTools.jsx'; 
import TutorialManager from './components/Tutorial/TutorialManager';
import { TutorialProvider } from './contexts/TutorialContext';
import BasemapControl from './components/Map/BasemapControl'; // Import BasemapControl
import './styles/font.css';
import './styles/mapLegend.css';
import './styles/metadata.css';
import './styles/profileMenu.css';
import './styles/drawingTools.css';
import './styles/BasemapControl.css'; // Import basemap control styles

// GlobalStyles component remains the same
const GlobalStyles = () => {
  useEffect(() => {
    // CSS variables to root - Google Dark Theme
    document.documentElement.style.setProperty('--color-primary', '138, 180, 248');
    document.documentElement.style.setProperty('--color-bg-dark', '24, 24, 24');
    document.documentElement.style.setProperty('--color-bg-medium', '48, 49, 52');
    document.documentElement.style.setProperty('--color-bg-light', '60, 64, 67');
    document.documentElement.style.setProperty('--color-accent', '253, 214, 99');
    document.documentElement.style.setProperty('--color-text', '232, 234, 237');
    document.documentElement.style.setProperty('--color-text-light', '154, 160, 166');
    document.documentElement.style.setProperty('--color-error', '242, 139, 130');
    document.documentElement.style.setProperty('--color-success', '129, 201, 149');
    document.documentElement.style.setProperty('--transition-default', 'all 0.2s ease');

    // Body background: Google dark theme
    document.body.style.backgroundColor = '#181818';
    document.body.style.color = '#e8eaed';
  }, []);

  return null;
};

function App() {
  const [notification, setNotification] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [sidebarExpanded, setSidebarExpanded] = useState(false);

  const toggleSidebar = (expanded) => {
    setSidebarExpanded(expanded);
  };

  const showNotification = (message, type = 'info', duration = 3000) => {
    setNotification({ id: Date.now(), message, type, duration });
  };

  const handleCloseNotification = () => {
    setNotification(null);
  }

  const showLoading = (message = 'Processing...') => {
    console.log("Showing loading:", message);
    setLoadingMessage(message);
    setIsLoading(true);
  };

  const hideLoading = () => {
    console.log("Hiding loading");
    setIsLoading(false);
    setLoadingMessage('');
  };

  return (
    <AuthProvider>
      <MapProvider>
        <TutorialProvider>
          <GlobalStyles />
          <Layout sidebarExpanded={sidebarExpanded} showNotification={showNotification}>
            <Sidebar
              showNotification={showNotification}
              onToggleSidebar={toggleSidebar}
            />
            <AppMap />
            <RightSidebar showNotification={showNotification} />
            
            {/* Add BasemapControl component */}
            <BasemapControl />
            
            <FloatingDrawingTools showNotification={showNotification} />
            
            <PromptForm
              showNotification={showNotification}
              showLoading={showLoading}
              hideLoading={hideLoading}
            />

            {notification && (
              <Notification
                key={notification.id}
                message={notification.message}
                type={notification.type}
                duration={notification.duration}
                onClose={handleCloseNotification}
              />
            )}

            {isLoading && (
              <StatusIndicator message={loadingMessage} />
            )}
            
          
            <TutorialManager />
          </Layout>
        </TutorialProvider>
      </MapProvider>
    </AuthProvider>
  );
}

export default App;