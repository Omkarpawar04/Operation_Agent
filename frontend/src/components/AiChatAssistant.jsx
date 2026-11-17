import React, { useState } from 'react';
import { MessageCircle, Sparkles, X } from 'lucide-react';
import CareerChatbotPage from './CareerChatbotPage.jsx';

// Keep the existing floating operation-agent entry point, but open the full
// FINXL assistant experience in a compact overlay on the current page.
export default function AiChatAssistant({ assessmentActive = false, user = null }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="finxl-chat-widget">
      {isOpen && (
        <div id="finxl-chat-widget-panel" className="finxl-chat-widget-panel" role="dialog" aria-label="FINXL AI Assistant">
          <CareerChatbotPage
            embedded
            assessmentActive={assessmentActive}
            user={user}
            onClose={() => setIsOpen(false)}
          />
        </div>
      )}
      <button
        type="button"
        className={`finxl-chat-widget-toggle${isOpen ? ' is-open' : ''}`}
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        aria-label={isOpen ? 'Close FINXL Assistant' : 'Open FINXL Assistant'}
        aria-controls="finxl-chat-widget-panel"
        title={isOpen ? 'Close assistant' : 'Open FINXL assistant'}
      >
        {isOpen ? <X size={25} /> : <><Sparkles size={17} /><MessageCircle size={25} /></>}
      </button>
    </div>
  );
}
