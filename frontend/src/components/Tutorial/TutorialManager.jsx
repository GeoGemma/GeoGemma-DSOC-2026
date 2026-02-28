// src/components/Tutorial/TutorialManager.jsx
import { useEffect } from 'react';
import { useTutorial } from '../../contexts/TutorialContext';
import TutorialPopup from './TutorialPopup';

const TutorialManager = () => {
  const { 
    tutorialState, 
    isShowingTutorial, 
    currentTutorial, 
    completeTutorial, 
    setCurrentTutorial, 
    setIsShowingTutorial,
    goToNextTutorial
  } = useTutorial();

  // Define tutorial content
  const tutorials = {
    welcome: {
      title: "Welcome to GeoGemma",
      content: "GeoGemma allows you to explore Earth observation data using natural language. Let's take a quick tour to get you started!",
      position: "center",
      target: null, // No specific target, centered on screen
      step: 1,
      totalSteps: 5,
      hasPrevious: false,
      hasNext: true
    },
    promptInput: {
      title: "Search for Earth Imagery",
      content: "Type natural language queries here to visualize satellite imagery. Try something like 'Show NDVI in Paris for 2023' or 'Surface water in Amsterdam'.",
      position: "top",
      target: ".prompt-form", // Updated to more specific selector
      step: 2,
      totalSteps: 5,
      hasPrevious: true,
      hasNext: true
    },
    sidebar: {
      title: "Access Tools & Chat",
      content: "The sidebar provides access to chat functionality and specialized Earth observation tools. Click to expand it anytime.",
      position: "right",
      target: ".sidebar-collapsed-top", // More specific target for sidebar
      step: 3,
      totalSteps: 5,
      hasPrevious: true,
      hasNext: true
    },
    mapControls: {
      title: "Explore Map Controls",
      content: "Access layer management, inspection tools, and information about your visualizations in this panel.",
      position: "left",
      target: ".sidebar-toggle-container", 
      step: 4,
      totalSteps: 5,
      hasPrevious: true,
      hasNext: true
    },
    layers: {
      title: "Manage Your Layers",
      content: "After adding imagery, you can view, toggle, and adjust layers in the Layers panel. Try adding your first visualization!",
      position: "left",
      target: ".sidebar-tab:first-child", 
      step: 5,
      totalSteps: 5,
      hasPrevious: true,
      hasNext: false
    }
  };

  // Log current tutorial for debugging
  useEffect(() => {
    if (currentTutorial) {
      console.log(`Current tutorial: ${currentTutorial}`);
    }
  }, [currentTutorial]);

  // Add highlight to target element
  useEffect(() => {
    if (isShowingTutorial && currentTutorial) {
      const tutorialInfo = tutorials[currentTutorial];
      if (tutorialInfo && tutorialInfo.target && tutorialInfo.target !== "#root") {
        const targetElement = document.querySelector(tutorialInfo.target);
        if (targetElement) {
          targetElement.classList.add('tutorial-highlight');
          return () => targetElement.classList.remove('tutorial-highlight');
        }
      }
    }
  }, [isShowingTutorial, currentTutorial]);

  // Skip all tutorials
  const skipAllTutorials = () => {
    const completedState = {
      hasSeenWelcome: true,
      hasSeenMapControls: true,
      hasSeenPromptInput: true,
      hasSeenSidebar: true,
      hasSeenLayers: true,
    };
    
    // Mark all tutorials as complete
    Object.keys(tutorials).forEach(key => {
      const tutorialKey = `hasSeen${key.charAt(0).toUpperCase() + key.slice(1)}`;
      completeTutorial(tutorialKey);
    });
    
    setIsShowingTutorial(false);
    setCurrentTutorial(null);
  };

  // Handle previous button
  const handlePrevious = () => {
    const sequence = Object.keys(tutorials);
    const currentIndex = sequence.indexOf(currentTutorial);
    
    if (currentIndex > 0) {
      setCurrentTutorial(sequence[currentIndex - 1]);
    }
  };

  // Handle complete/next button
  const handleComplete = () => {
    // First mark current tutorial as completed
    const tutorialKey = `hasSeen${currentTutorial.charAt(0).toUpperCase() + currentTutorial.slice(1)}`;
    console.log(`Completing tutorial: ${currentTutorial}, setting key: ${tutorialKey}`);
    completeTutorial(tutorialKey);
    
    // Then explicitly move to next tutorial
    goToNextTutorial();
  };

  if (!isShowingTutorial || !currentTutorial || !tutorials[currentTutorial]) {
    return null;
  }

  const tutorialInfo = tutorials[currentTutorial];

  return (
    <TutorialPopup
      title={tutorialInfo.title}
      content={tutorialInfo.content}
      position={tutorialInfo.position}
      target={tutorialInfo.target}
      step={tutorialInfo.step}
      totalSteps={tutorialInfo.totalSteps}
      hasPrevious={tutorialInfo.hasPrevious}
      hasNext={tutorialInfo.hasNext}
      onComplete={handleComplete}
      onSkip={skipAllTutorials}
      onPrevious={handlePrevious}
    />
  );
};

export default TutorialManager;