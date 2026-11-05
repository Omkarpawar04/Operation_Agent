import React, { useState } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';

export default function VoiceAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { sender: 'ai', text: 'Hello! I am your AI Mock Interviewer. How can I help you prepare today?' }
  ]);
  const [input, setInput] = useState('');

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages((prev) => [...prev, { sender: 'user', text: input }]);
    const userQuery = input;
    setInput('');

    // Simulate AI response for mock interview
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: `That's a great point regarding "${userQuery}". Let's dive deeper into your technical project experience. Can you explain your architecture choices?` }
      ]);
    }, 1000);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* 3D Unique Animated Chat Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative group flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-tr from-purple-600 via-indigo-600 to-pink-500 text-white shadow-2xl transform transition-all duration-300 hover:scale-110 hover:rotate-6 active:scale-95 focus:outline-none ring-4 ring-purple-300/50 animate-pulse"
      >
        {/* Glow effect */}
        <span className="absolute inset-0 rounded-full bg-gradient-to-r from-pink-500 to-purple-600 blur-md opacity-75 group-hover:opacity-100 transition duration-300 -z-10"></span>
        
        {/* Icon toggle */}
        {isOpen ? (
          <X className="w-7 h-7 transition-transform duration-300 rotate-90 scale-100" />
        ) : (
          <MessageCircle className="w-7 h-7 transition-transform duration-300 scale-100 group-hover:scale-110" />
        )}
      </button>

      {/* Pop-up Chat Window */}
      {isOpen && (
        <div className="absolute bottom-20 right-0 w-80 sm:w-96 h-[450px] bg-white rounded-2xl shadow-2xl border border-gray-100 flex flex-col overflow-hidden transition-all duration-300 animate-in fade-in slide-in-from-bottom-5">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 p-4 text-white font-semibold flex justify-between items-center shadow-md">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-green-400 rounded-full animate-ping"></span>
              <span>AI Mock Interviewer</span>
            </div>
            <button 
              onClick={() => setIsOpen(false)} 
              className="text-white hover:text-gray-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages Body */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-gray-50 text-sm">
            {messages.map((msg, index) => (
              <div 
                key={index} 
                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`max-w-[80%] p-3 rounded-xl shadow-sm ${
                    msg.sender === 'user' 
                      ? 'bg-purple-600 text-white rounded-br-none' 
                      : 'bg-white text-gray-800 border border-gray-100 rounded-bl-none'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
          </div>

          {/* Input Footer */}
          <form onSubmit={handleSend} className="p-3 border-t border-gray-100 bg-white flex gap-2 items-center">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your interview answer..." 
              className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-gray-50"
            />
            <button 
              type="submit" 
              className="bg-purple-600 text-white p-2.5 rounded-xl hover:bg-purple-700 transition-colors shadow-md"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}