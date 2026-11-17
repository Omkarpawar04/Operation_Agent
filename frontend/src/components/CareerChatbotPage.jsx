import React, { useEffect, useRef, useState } from 'react';
import { Bot, Maximize2, Minimize2, RotateCcw, Send, Settings2, Sparkles, User, X } from 'lucide-react';
import { CHATBOT_OPTIONS } from './chatbotFaqs.js';
import '../chatbot.css';

export default function CareerChatbotPage({ assessmentActive = false, user = null, embedded = false, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [responseStyle, setResponseStyle] = useState('balanced');
  const [fullscreen, setFullscreen] = useState(false);
  const [selectedOptionId, setSelectedOptionId] = useState(null);
  const threadRef = useRef(null);
  const displayName = user?.name?.trim().split(/\s+/)[0];
  const selectedOption = CHATBOT_OPTIONS.find((option) => option.id === selectedOptionId);

  // Scroll the chat's own viewport. scrollIntoView can also move the outer page,
  // which made the standalone demo look blank after an AI response arrived.
  useEffect(() => {
    const thread = threadRef.current;
    if (thread) thread.scrollTo({ top: thread.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  const sendMessage = async (text = input) => {
    const content = text.trim();
    if (!content || busy || assessmentActive) return;
    const prior = messages;
    setMessages([...prior, { role: 'user', content }]);
    setInput('');
    setError('');
    setBusy(true);
    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          history: prior.slice(-12).map(({ role, content: message }) => ({ role, content: message })),
          assessment_active: assessmentActive,
          response_style: responseStyle,
          user_context: { name: user?.name || '', role: user?.role || '' },
        }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data?.success) throw new Error(data?.error || 'Could not reach the assistant. Please try again.');
      if (typeof data.reply !== 'string' || !data.reply.trim()) {
        throw new Error('The assistant returned an empty reply. Please try again.');
      }
      setMessages((current) => [...current, { role: 'assistant', content: data.reply.trim() }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const showFixedAnswer = (option, item) => {
    if (assessmentActive) return;
    setMessages((current) => [
      ...current,
      { role: 'user', content: item.question },
      { role: 'assistant', content: item.answer, sourceTitle: option.title },
    ]);
    setError('');
  };

  const clearChat = () => {
    setMessages([]);
    setError('');
    setInput('');
    setSelectedOptionId(null);
  };

  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.querySelector('.career-chat-shell')?.requestFullscreen();
        setFullscreen(true);
      } else {
        await document.exitFullscreen();
        setFullscreen(false);
      }
    } catch {
      setFullscreen(Boolean(document.fullscreenElement));
    }
  };

  const optionButtons = (compact = false) => CHATBOT_OPTIONS.map((option) => {
    const Icon = option.icon;
    const selected = option.id === selectedOptionId;
    return (
      <button
        type="button"
        key={option.id}
        className={`career-chat-option${selected ? ' is-selected' : ''}${compact ? ' is-compact' : ''}`}
        onClick={() => setSelectedOptionId(selected ? null : option.id)}
        disabled={assessmentActive}
        aria-pressed={selected}
      >
        <span className="career-chat-option-icon"><Icon size={compact ? 14 : 17} /></span>
        <span className="career-chat-option-copy"><b>{option.title}</b>{!compact && <small>{option.description}</small>}</span>
      </button>
    );
  });

  const faqPanel = selectedOption && (
    <div className="career-chat-faq-panel">
      <div className="career-chat-faq-heading">
        <div><b>{selectedOption.title}</b><span>Choose a popular question for an instant answer</span></div>
        <button type="button" onClick={() => setSelectedOptionId(null)} aria-label="Close suggested questions"><X size={15} /></button>
      </div>
      <div className="career-chat-faq-list">
        {selectedOption.questions.map((item) => (
          <button key={item.question} type="button" onClick={() => showFixedAnswer(selectedOption, item)} disabled={assessmentActive}>
            {item.question}<span>↗</span>
          </button>
        ))}
      </div>
      <p className="career-chat-faq-note">These answers are built in and work without Gemini.</p>
    </div>
  );

  return (
    <div className={`career-chat-shell${fullscreen ? ' is-fullscreen' : ''}${embedded ? ' is-embedded' : ''}`}>
      <div className="career-chat-aurora" aria-hidden="true" />

      <header className="career-chat-header">
        <div className="career-chat-brand">
          <div className="career-chat-logo"><Sparkles size={18} /></div>
          <div><b>FINXL</b><span>AI ASSISTANT</span></div>
        </div>
        <div className="career-chat-header-actions">
          <span className="career-chat-context-label">Career + everyday help</span>
          {!embedded && <button type="button" className="career-chat-icon-btn" onClick={toggleFullscreen} aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'} title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
            {fullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>}
          <div className="career-chat-settings-wrap">
            <button type="button" className={`career-chat-icon-btn${settingsOpen ? ' is-selected' : ''}`} onClick={() => setSettingsOpen((value) => !value)} aria-label="Chat settings" title="Chat settings"><Settings2 size={19} /></button>
            {settingsOpen && (
              <div className="career-chat-settings" role="dialog" aria-label="Chat settings">
                <div className="career-chat-settings-top"><b>Chat settings</b><button type="button" onClick={() => setSettingsOpen(false)} aria-label="Close settings"><X size={15} /></button></div>
                <label htmlFor="response-style">Response length</label>
                <select id="response-style" value={responseStyle} onChange={(event) => setResponseStyle(event.target.value)}>
                  <option value="concise">Short</option>
                  <option value="balanced">Balanced</option>
                  <option value="detailed">Detailed</option>
                </select>
                <p>Career guidance is tailored to your platform role. Ask general questions too.</p>
              </div>
            )}
          </div>
          <button type="button" className="career-chat-icon-btn" onClick={clearChat} aria-label="Start a new chat" title="New chat"><RotateCcw size={17} /></button>
          {embedded && <button type="button" className="career-chat-icon-btn career-chat-close-btn" onClick={onClose} aria-label="Close chatbot" title="Close chatbot"><X size={18} /></button>}
        </div>
      </header>

      <div className="career-chat-stage">
        <div className="career-chat-bot-scene" aria-hidden="true">
          <div className="career-chat-bot-glow" />
          <div className="career-bot">
            <div className="career-bot-ear career-bot-ear-left" />
            <div className="career-bot-ear career-bot-ear-right" />
            <div className="career-bot-antenna"><i /></div>
            <div className="career-bot-head"><div className="career-bot-face"><i /><i /><b /></div></div>
            <div className="career-bot-neck" />
            <div className="career-bot-body"><div className="career-bot-chest-light" /></div>
            <div className="career-bot-arm career-bot-arm-left" />
            <div className="career-bot-arm career-bot-arm-right" />
          </div>
          <div className="career-bot-shadow" />
        </div>

        <section className={`career-chat-content${messages.length ? ' has-messages' : ''}`} aria-live="polite">
          {assessmentActive && <div role="status" className="career-chat-assessment-lock"><b>Assistant paused during your assessment.</b><span>Finish or submit your quiz before chatting again.</span></div>}
          {!messages.length ? (
            <div className="career-chat-welcome">
              <span className="career-chat-eyebrow"><span /> READY WHEN YOU ARE</span>
              <h1>{displayName ? `Hey ${displayName}, welcome!` : 'Hey, welcome!'}</h1>
              <p>Choose a topic or ask me anything.</p>
              <div className="career-chat-option-grid">{optionButtons()}</div>
              {faqPanel}
            </div>
          ) : (
            <div className="career-chat-thread" ref={threadRef}>
              <div className="career-chat-thread-title"><span><Bot size={16} /> Your conversation</span><button type="button" onClick={clearChat}>New chat</button></div>
              <div className="career-chat-option-strip">{optionButtons(true)}</div>
              {faqPanel}
              {messages.map((message, index) => (
                <div key={`${index}-${message.role}-${index}`} className={`career-chat-message ${message.role}`}>
                  <div className="career-chat-message-avatar">{message.role === 'user' ? <User size={15} /> : <Bot size={16} />}</div>
                  <div className="career-chat-message-body"><span>{message.role === 'user' ? 'YOU' : message.sourceTitle || 'FINXL ASSISTANT'}</span><p>{message.content}</p></div>
                </div>
              ))}
              {busy && <div className="career-chat-thinking"><span /><span /><span /> <em>Thinking</em></div>}
              {error && <div role="alert" className="career-chat-error">{error}</div>}
            </div>
          )}
        </section>

        <form onSubmit={(event) => { event.preventDefault(); sendMessage(); }} className="career-chat-composer-wrap">
          <div className={`career-chat-composer${assessmentActive ? ' is-disabled' : ''}`}>
            <label className="sr-only" htmlFor="career-chat-input">Message FINXL Assistant</label>
            <textarea id="career-chat-input" rows={1} maxLength={2000} value={input} disabled={assessmentActive} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder={assessmentActive ? 'Chat paused until your quiz is submitted' : 'Ask FINXL Assistant anything…'} />
            <button type="submit" disabled={busy || assessmentActive || !input.trim()} aria-label="Send message" title="Send message"><Send size={19} /></button>
          </div>
          <div className="career-chat-footer"><span><Sparkles size={12} /> Instant guides, career help, and general answers</span><span>AI can make mistakes</span></div>
        </form>
      </div>
    </div>
  );
}
