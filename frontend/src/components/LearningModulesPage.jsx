import React from 'react';
import CourseManager from './learning/CourseManager.jsx';
import TrainerReleases from './learning/TrainerReleases.jsx';
import StudentLearning from './learning/StudentLearning.jsx';

// One tab, three views: Admin builds courses, the Trainer opens topics per batch, the Student watches what is open.
// Operations sees the courses read-only.
export default function LearningModulesPage({ token, role, onSessionExpired }) {
  if (role === 'Trainer') return <TrainerReleases token={token} onSessionExpired={onSessionExpired} />;
  if (role === 'Student') return <StudentLearning token={token} onSessionExpired={onSessionExpired} />;
  return <CourseManager token={token} canEdit={role === 'Admin'} onSessionExpired={onSessionExpired} />;
}
