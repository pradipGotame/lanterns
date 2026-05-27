import React, { useState, useEffect } from 'react';
import { Trash2, Plus, Play } from 'lucide-react';

// ============================================
// FileUploader Component
// ============================================
const FileUploader = ({ tabName, files, onFileAdd, onFileDelete }) => {
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    selectedFiles.forEach(file => {
      onFileAdd(tabName, file);
    });
    e.target.value = '';
  };

  return (
    <div className="space-y-4">
      <div className="border-2 border-dashed border-blue-300 rounded-lg p-6 bg-blue-50">
        <label className="flex items-center justify-center cursor-pointer">
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
          <div className="text-center">
            <Plus className="mx-auto mb-2 text-blue-600" size={32} />
            <p className="text-blue-600 font-medium">Click to upload files</p>
            <p className="text-sm text-gray-600">or drag and drop</p>
          </div>
        </label>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-700">Uploaded Files:</h4>
          <div className="space-y-2">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between bg-white p-3 rounded-lg border border-gray-200 hover:border-gray-300 transition"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
                <button
                  onClick={() => onFileDelete(tabName, index)}
                  className="ml-3 p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
                  title="Delete file"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================
// TabContent Component
// ============================================
const TabContent = ({ tabName, files, onFileAdd, onFileDelete, isActive }) => {
  if (!isActive) return null;

  return (
    <div className="p-6 bg-white">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        {tabName} Files
      </h3>
      <FileUploader
        tabName={tabName}
        files={files}
        onFileAdd={onFileAdd}
        onFileDelete={onFileDelete}
      />
    </div>
  );
};

// ============================================
// ProjectTabs Component
// ============================================
const ProjectTabs = ({ projectName, files, onFileAdd, onFileDelete, onStart, isLoading }) => {
  const [activeTab, setActiveTab] = useState('Requirement');
  const tabs = ['Requirement', 'Test', 'Code'];

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Tab Headers */}
      <div className="flex border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-4 px-6 font-medium transition ${
              activeTab === tab
                ? 'border-b-2 border-blue-600 text-blue-600 bg-blue-50'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tabs.map((tab) => (
        <TabContent
          key={tab}
          tabName={tab}
          files={files[tab] || []}
          onFileAdd={onFileAdd}
          onFileDelete={onFileDelete}
          isActive={activeTab === tab}
        />
      ))}

      {/* Start Button */}
      <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end">
        <button
          onClick={onStart}
          disabled={isLoading}
          className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg transition"
        >
          <Play size={20} />
          {isLoading ? 'Starting...' : 'Start'}
        </button>
      </div>
    </div>
  );
};

// ============================================
// ProjectForm Component
// ============================================
const ProjectForm = ({ onProjectCreate }) => {
  const [projectName, setProjectName] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (projectName.trim()) {
      onProjectCreate(projectName.trim());
      setProjectName('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-bold text-gray-800 mb-4">Create New Project</h2>
      <div className="flex gap-3">
        <input
          type="text"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="Enter project name"
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition flex items-center gap-2"
        >
          <Plus size={20} />
          Create
        </button>
      </div>
    </form>
  );
};

// ============================================
// ProjectList Component
// ============================================
const ProjectList = ({ projects, onSelectProject, onDeleteProject }) => {
  if (projects.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-lg font-bold text-gray-800 mb-4">Your Projects</h2>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {projects.map((project) => (
          <div
            key={project.id}
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
          >
            <button
              onClick={() => onSelectProject(project.id)}
              className="flex-1 text-left text-gray-800 font-medium hover:text-blue-600 transition"
            >
              {project.name}
            </button>
            <button
              onClick={() => onDeleteProject(project.id)}
              className="ml-3 p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
              title="Delete project"
            >
              <Trash2 size={18} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================
// Main App Component
// ============================================
export default function ProjectManager() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [files, setFiles] = useState({ Requirement: [], Test: [], Code: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Load projects from localStorage on mount
  useEffect(() => {
    const savedProjects = localStorage.getItem('projects');
    if (savedProjects) {
      setProjects(JSON.parse(savedProjects));
    }
  }, []);

  // Load files for selected project
  useEffect(() => {
    if (selectedProjectId) {
      const projectFiles = localStorage.getItem(`project_${selectedProjectId}_files`);
      if (projectFiles) {
        setFiles(JSON.parse(projectFiles));
      } else {
        setFiles({ Requirement: [], Test: [], Code: [] });
      }
    }
  }, [selectedProjectId]);

  // Save projects to localStorage
  const saveProjects = (updatedProjects) => {
    setProjects(updatedProjects);
    localStorage.setItem('projects', JSON.stringify(updatedProjects));
  };

  // Save files to localStorage
  const saveFiles = (updatedFiles) => {
    setFiles(updatedFiles);
    if (selectedProjectId) {
      localStorage.setItem(`project_${selectedProjectId}_files`, JSON.stringify(updatedFiles));
    }
  };

  const handleProjectCreate = (projectName) => {
    const newProject = {
      id: Date.now().toString(),
      name: projectName,
      createdAt: new Date().toISOString(),
    };
    const updatedProjects = [...projects, newProject];
    saveProjects(updatedProjects);
    setSelectedProjectId(newProject.id);
    setFiles({ Requirement: [], Test: [], Code: [] });
  };

  const handleProjectSelect = (projectId) => {
    setSelectedProjectId(projectId);
  };

  const handleDeleteProject = (projectId) => {
    const updatedProjects = projects.filter((p) => p.id !== projectId);
    saveProjects(updatedProjects);
    localStorage.removeItem(`project_${projectId}_files`);
    if (selectedProjectId === projectId) {
      setSelectedProjectId(null);
      setFiles({ Requirement: [], Test: [], Code: [] });
    }
  };

  const handleFileAdd = (tabName, file) => {
    const updatedFiles = { ...files };
    updatedFiles[tabName] = [...(updatedFiles[tabName] || []), file];
    saveFiles(updatedFiles);
  };

  const handleFileDelete = (tabName, fileIndex) => {
    const updatedFiles = { ...files };
    updatedFiles[tabName] = updatedFiles[tabName].filter((_, i) => i !== fileIndex);
    saveFiles(updatedFiles);
  };

  const handleStart = async () => {
    if (!selectedProjectId) {
      alert('Please select or create a project first');
      return;
    }

    setIsLoading(true);
    try {
      const selectedProject = projects.find((p) => p.id === selectedProjectId);

      // Prepare FormData for file upload
      const formData = new FormData();
      formData.append('projectName', selectedProject.name);
      formData.append('projectId', selectedProjectId);

      // Add files from each tab
      Object.keys(files).forEach((tabName) => {
        files[tabName].forEach((file, index) => {
          formData.append(`${tabName}_${index}`, file);
        });
      });

      // Send to backend API
      const response = await fetch('http://localhost:5000/api/projects/start', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        setSuccessMessage(`Project "${selectedProject.name}" started successfully!`);
        setTimeout(() => setSuccessMessage(''), 3000);
      } else {
        alert('Error starting project. Please check your backend connection.');
      }
    } catch (error) {
      console.error('Error starting project:', error);
      alert('Failed to start project. Make sure backend is running at http://localhost:5000');
    } finally {
      setIsLoading(false);
    }
  };

  const currentProject = selectedProjectId
    ? projects.find((p) => p.id === selectedProjectId)
    : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Project Manager</h1>
          <p className="text-gray-600">Create projects and upload files for requirements, tests, and code</p>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 p-4 bg-green-100 border border-green-400 text-green-800 rounded-lg">
            {successMessage}
          </div>
        )}

        {/* Create Project Form */}
        <ProjectForm onProjectCreate={handleProjectCreate} />

        {/* Project List */}
        <ProjectList
          projects={projects}
          onSelectProject={handleProjectSelect}
          onDeleteProject={handleDeleteProject}
        />

        {/* Project Tabs */}
        {currentProject && (
          <div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Working on: {currentProject.name}
            </h2>
            <ProjectTabs
              projectName={currentProject.name}
              files={files}
              onFileAdd={handleFileAdd}
              onFileDelete={handleFileDelete}
              onStart={handleStart}
              isLoading={isLoading}
            />
          </div>
        )}

        {!currentProject && projects.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
            <p className="text-blue-800">
              Select a project from the list above to get started
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
