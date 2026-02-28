// src/components/Sidebar/ChatInput.jsx
import { useState } from 'react';
import PropTypes from 'prop-types';
import { Send, Loader } from 'lucide-react';

const ChatInput = ({ onSendMessage, isLoading }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!message.trim()) return;
    
    onSendMessage(message);
    setMessage('');
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-container">
      <div className="relative flex items-center">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Message GeoGemma..."
          className="chat-input"
          disabled={isLoading}
        />
        <button 
          type="submit"
          className={`chat-submit-btn ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
          disabled={isLoading || !message.trim()}
        >
          {isLoading ? (
            <Loader size={18} className="animate-spin" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>
    </form>
  );
};

ChatInput.propTypes = {
  onSendMessage: PropTypes.func.isRequired,
  isLoading: PropTypes.bool
};

ChatInput.defaultProps = {
  isLoading: false
};

export default ChatInput;