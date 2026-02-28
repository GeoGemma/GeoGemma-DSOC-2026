// src/contexts/TutorialContext.jsx
import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';
import { db } from '../services/firebase';
import { doc, getDoc, setDoc } from 'firebase/firestore';

const TutorialContext = createContext(null);

export function TutorialProvider({ children }) {
  const [tutorialState, setTutorialState] = useState({
    hasSeenWelcome: false,
    hasSeenMapControls: false,
    hasSeenPromptInput: false,
    hasSeenSidebar: false,
    hasSeenLayers: false,
  });
  const [isShowingTutorial, setIsShowingTutorial] = useState(false);
  const [currentTutorial, setCurrentTutorial] = useState(null);
  const { currentUser } = useAuth();
  const prevUserRef = useRef(null);

  // Load tutorial state from Firestore for logged-in users
  useEffect(() => {
    const loadTutorialState = async () => {
      // For testing: Get the forceShowTutorial flag from localStorage
      const forceShowTutorial = localStorage.getItem('forceShowTutorial') === 'true';
      
      // Only trigger on new sign-in
      if (currentUser && !prevUserRef.current) {
        try {
          const tutorialDocRef = doc(db, "userPreferences", currentUser.uid);
          const docSnap = await getDoc(tutorialDocRef);
          
          if (docSnap.exists() && docSnap.data().tutorials && !forceShowTutorial) {
            setTutorialState(docSnap.data().tutorials);
            // Check if all tutorials are completed
            const allCompleted = Object.values(docSnap.data().tutorials).every(Boolean);
            if (!allCompleted) {
              setIsShowingTutorial(true);
              setCurrentTutorial('welcome');
            } else {
              setIsShowingTutorial(false);
              setCurrentTutorial(null);
            }
          } else {
            // First-time user or forcing tutorial, show tutorials
            setIsShowingTutorial(true);
            setCurrentTutorial('welcome');
          }
        } catch (error) {
          console.error("Error loading tutorial state:", error);
        }
      } else if (!currentUser) {
        setIsShowingTutorial(false);
        setCurrentTutorial(null);
      }
      prevUserRef.current = currentUser;
    };
    
    loadTutorialState();
  }, [currentUser]);

  // Save tutorial state to Firestore
  const saveTutorialState = async (newState) => {
    if (currentUser) {
      try {
        const tutorialDocRef = doc(db, "userPreferences", currentUser.uid);
        await setDoc(tutorialDocRef, { 
          tutorials: newState 
        }, { merge: true });
      } catch (error) {
        console.error("Error saving tutorial state:", error);
      }
    }
  };

  // Mark a tutorial as completed
  const completeTutorial = (tutorialKey) => {
    console.log(`Marking tutorial as completed: ${tutorialKey}`);
    
    const newState = {
      ...tutorialState,
      [tutorialKey]: true
    };
    
    setTutorialState(newState);
    saveTutorialState(newState);
  };

  // Define tutorial sequence
  const advanceToNextTutorial = (tutorialKey) => {
    // Convert from property name (like 'hasSeenWelcome') to tutorial key ('welcome')
    let tutorialName = tutorialKey;
    if (tutorialKey.startsWith('hasSeen')) {
      tutorialName = tutorialKey.substring(7); // Remove 'hasSeen'
      tutorialName = tutorialName.charAt(0).toLowerCase() + tutorialName.slice(1); // Lowercase first letter
    }
    
    const sequence = ['welcome', 'promptInput', 'sidebar', 'mapControls', 'layers'];
    const currentIndex = sequence.indexOf(tutorialName);
    
    console.log(`Advancing from tutorial: ${tutorialName}, index: ${currentIndex}`);
    
    if (currentIndex !== -1 && currentIndex < sequence.length - 1) {
      const nextTutorial = sequence[currentIndex + 1];
      console.log(`Moving to next tutorial: ${nextTutorial}`);
      setCurrentTutorial(nextTutorial);
    } else {
      // End of tutorials
      console.log("End of tutorials reached");
      setIsShowingTutorial(false);
      setCurrentTutorial(null);
    }
  };

  // Manual advance to next tutorial
  const goToNextTutorial = () => {
    if (!currentTutorial) return;
    
    const sequence = ['welcome', 'promptInput', 'sidebar', 'mapControls', 'layers'];
    const currentIndex = sequence.indexOf(currentTutorial);
    
    if (currentIndex !== -1 && currentIndex < sequence.length - 1) {
      const nextTutorial = sequence[currentIndex + 1];
      setCurrentTutorial(nextTutorial);
    } else {
      // End of tutorials
      setIsShowingTutorial(false);
      setCurrentTutorial(null);
    }
  };

  // Restart tutorials
  const restartTutorials = () => {
    const resetState = {
      hasSeenWelcome: false,
      hasSeenMapControls: false,
      hasSeenPromptInput: false,
      hasSeenSidebar: false,
      hasSeenLayers: false,
    };
    
    setTutorialState(resetState);
    saveTutorialState(resetState);
    setIsShowingTutorial(true);
    setCurrentTutorial('welcome');
  };

  const value = {
    tutorialState,
    isShowingTutorial,
    currentTutorial,
    completeTutorial,
    restartTutorials,
    setCurrentTutorial,
    setIsShowingTutorial,
    goToNextTutorial,
    advanceToNextTutorial
  };

  return <TutorialContext.Provider value={value}>{children}</TutorialContext.Provider>;
}

export function useTutorial() {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error('useTutorial must be used within a TutorialProvider');
  }
  return context;
}