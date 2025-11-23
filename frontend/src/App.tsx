import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Requirements from './pages/Requirements';
import ProjectConfiguration from './pages/ProjectConfiguration';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <div className="min-h-screen bg-background text-white selection:bg-primary selection:text-black">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/requirements" element={<Requirements />} />
            <Route path="/configure/:projectId" element={<ProjectConfiguration />} />
            <Route path="/dashboard/:projectId" element={<Dashboard />} />
            <Route path="/chat/:projectId" element={<Chat />} />
          </Routes>
        </div>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
