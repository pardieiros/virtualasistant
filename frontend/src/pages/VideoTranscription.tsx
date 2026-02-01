import { useState, useRef, useEffect } from 'react';
import { videoAPI, sttAPI, videoTranscriptionAPI } from '../api/client';
import type { VideoTranscription } from '../types';

interface JobStatus {
  id: string;
  filename: string;
  status: 'queued' | 'processing' | 'done' | 'error';
  lang: string;
  model: string;
  diarize: boolean;
  created_at?: number;
  started_at?: number;
  logs?: Array<{
    ts: number;
    stage: string;
    progress: number;
    message: string;
  }>;
}

interface TranscriptionResult {
  job_id: string;
  diarization: boolean;
  language: string;
  text: string;
}

type TabType = 'new' | 'saved';

const VideoTranscription = () => {
  const [activeTab, setActiveTab] = useState<TabType>('new');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [transcriptionResult, setTranscriptionResult] = useState<TranscriptionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string>('');
  const [currentProgress, setCurrentProgress] = useState(0);
  const [currentMessage, setCurrentMessage] = useState<string>('');
  
  // Saved transcriptions
  const [savedTranscriptions, setSavedTranscriptions] = useState<VideoTranscription[]>([]);
  const [selectedTranscription, setSelectedTranscription] = useState<VideoTranscription | null>(null);
  const [isLoadingSaved, setIsLoadingSaved] = useState(false);
  
  // Speaker identification modal
  const [showSpeakerModal, setShowSpeakerModal] = useState(false);
  const [speakerMappings, setSpeakerMappings] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Language and model options
  const [selectedLang, setSelectedLang] = useState('pt');
  const [selectedModel, setSelectedModel] = useState('small');
  const [diarize, setDiarize] = useState(true);

  // Load saved transcriptions when switching to saved tab
  useEffect(() => {
    if (activeTab === 'saved') {
      loadSavedTranscriptions();
    }
  }, [activeTab]);

  // Extract unique speakers from transcription text
  const extractSpeakers = (text: string): string[] => {
    const speakerRegex = /\[.*?\]\s*(User\d+):/g;
    const matches = Array.from(text.matchAll(speakerRegex));
    const speakers = new Set<string>();
    matches.forEach(match => {
      if (match[1]) {
        speakers.add(match[1]);
      }
    });
    return Array.from(speakers).sort();
  };

  // Load saved transcriptions
  const loadSavedTranscriptions = async () => {
    setIsLoadingSaved(true);
    try {
      const transcriptions = await videoTranscriptionAPI.list();
      setSavedTranscriptions(transcriptions);
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to load saved transcriptions');
    } finally {
      setIsLoadingSaved(false);
    }
  };

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        if ((eventSourceRef.current as any).__pollInterval) {
          clearInterval((eventSourceRef.current as any).__pollInterval);
        }
      }
    };
  }, []);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm'];
      if (!allowedTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|mkv|webm)$/i)) {
        setError('Invalid file type. Please select a video file (MP4, AVI, MOV, MKV, or WebM).');
        return;
      }
      
      // Validate file size (2GB limit)
      const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024; // 2GB
      if (file.size > MAX_FILE_SIZE) {
        const fileSizeGB = (file.size / (1024 * 1024 * 1024)).toFixed(2);
        setError(`File too large. Maximum size is 2GB. Your file is ${fileSizeGB}GB.`);
        return;
      }
      
      setSelectedFile(file);
      setError(null);
      setUploadedFilename(null);
      setJobId(null);
      setJobStatus(null);
      setTranscriptionResult(null);
      setUploadProgress(0);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      const result = await videoAPI.upload(selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      if (result.success) {
        setUploadedFilename(result.filename);
      } else {
        setError('Upload failed');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const startTranscription = async (filename: string) => {
    try {
      setError(null);
      setCurrentStage('queued');
      setCurrentProgress(0);
      setCurrentMessage('Starting transcription job...');
      
      const result = await sttAPI.createJob(filename, selectedLang, selectedModel, diarize);
      setJobId(result.job_id);
      
      pollJobStatus(result.job_id);
      subscribeToJobEvents(result.job_id);
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to start transcription');
      setCurrentStage('error');
      setCurrentMessage('Failed to start transcription');
    }
  };

  const pollJobStatus = async (id: string) => {
    try {
      const status = await sttAPI.getJobStatus(id);
      setJobStatus(status);
      
      if (status.logs && status.logs.length > 0) {
        const latestLog = status.logs[status.logs.length - 1];
        const newStage = latestLog.stage || status.status;
        const newProgress = latestLog.progress || 0;
        const newMessage = latestLog.message || '';
        
        setCurrentStage(newStage);
        setCurrentProgress(newProgress);
        setCurrentMessage(newMessage);
      } else {
        setCurrentStage(status.status);
        setCurrentProgress(0);
        setCurrentMessage(`Status: ${status.status}`);
      }
      
      if (status.status === 'done') {
        try {
          const result = await sttAPI.getJobResult(id);
          setTranscriptionResult(result);
          if (eventSourceRef.current && (eventSourceRef.current as any).__pollInterval) {
            clearInterval((eventSourceRef.current as any).__pollInterval);
            (eventSourceRef.current as any).__pollInterval = null;
          }
        } catch (err: any) {
          if (err.response?.status !== 409) {
            console.error('Error getting result:', err);
          }
        }
      } else if (status.status === 'error') {
        const errorMsg = status.error || 'Transcription failed';
        setError(errorMsg);
        if (eventSourceRef.current && (eventSourceRef.current as any).__pollInterval) {
          clearInterval((eventSourceRef.current as any).__pollInterval);
          (eventSourceRef.current as any).__pollInterval = null;
        }
      }
    } catch (err: any) {
      console.error(`[Poll] Error polling job ${id} status:`, err);
    }
  };

  const subscribeToJobEvents = (id: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      if ((eventSourceRef.current as any).__pollInterval) {
        clearInterval((eventSourceRef.current as any).__pollInterval);
      }
    }

    const pollInterval = setInterval(() => {
      pollJobStatus(id);
    }, 2000);
    
    try {
      const eventSource = sttAPI.subscribeToJobEvents(id, (event) => {
        setCurrentStage(event.stage || '');
        setCurrentProgress(event.progress || 0);
        setCurrentMessage(event.message || '');
        pollJobStatus(id);
        
        if (event.stage === 'done') {
          setTimeout(() => {
            pollJobStatus(id);
            if (pollInterval) {
              clearInterval(pollInterval);
            }
          }, 1000);
        } else if (event.stage === 'error') {
          setError('Transcription error occurred');
          eventSource.close();
          if (pollInterval) {
            clearInterval(pollInterval);
          }
        }
      });

      eventSourceRef.current = eventSource;
      eventSource.onerror = (error) => {
        console.warn(`[SSE] Error for job ${id}, continuing with polling:`, error);
      };
      
      (eventSource as any).__pollInterval = pollInterval;
    } catch (error) {
      console.warn(`[SSE] Connection failed for job ${id}, using polling only:`, error);
      (eventSourceRef.current as any) = { __pollInterval: pollInterval };
    }
  };

  const handleSaveTranscription = () => {
    if (!transcriptionResult || !uploadedFilename) {
      setError('No transcription to save');
      return;
    }

    // Extract speakers from transcription
    const speakers = extractSpeakers(transcriptionResult.text);
    
    // Initialize speaker mappings
    const initialMappings: Record<string, string> = {};
    speakers.forEach(speaker => {
      initialMappings[speaker] = '';
    });
    
    setSpeakerMappings(initialMappings);
    setShowSpeakerModal(true);
  };

  const handleSaveWithSpeakers = async () => {
    if (!transcriptionResult || !uploadedFilename) {
      return;
    }

    setIsSaving(true);
    try {
      // Create transcription with speaker mappings already included
      const transcription = await videoTranscriptionAPI.create({
        filename: uploadedFilename,
        transcription_text: transcriptionResult.text,
        language: transcriptionResult.language,
        diarization_enabled: transcriptionResult.diarization,
        speaker_mappings: speakerMappings,
      });

      // Only update speakers if there are non-empty mappings (names provided)
      const hasNonEmptyMappings = Object.values(speakerMappings).some(name => name.trim() !== '');
      if (hasNonEmptyMappings) {
        try {
          await videoTranscriptionAPI.updateSpeakers(transcription.id, speakerMappings);
        } catch (updateErr: any) {
          // If update fails, log but don't fail the whole save
          console.warn('Failed to update speaker mappings:', updateErr);
        }
      }

      setShowSpeakerModal(false);
      setError(null);
      
      // Switch to saved tab and reload
      setActiveTab('saved');
      await loadSavedTranscriptions();
      
      // Reset transcription form
      handleReset();
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to save transcription');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setUploadedFilename(null);
    setJobId(null);
    setJobStatus(null);
    setTranscriptionResult(null);
    setError(null);
    setCurrentStage('');
    setCurrentProgress(0);
    setCurrentMessage('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  const handleViewTranscription = async (id: number) => {
    try {
      const transcription = await videoTranscriptionAPI.get(id);
      setSelectedTranscription(transcription);
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to load transcription');
    }
  };

  const handleDeleteTranscription = async (id: number) => {
    if (!confirm('Are you sure you want to delete this transcription?')) {
      return;
    }

    try {
      await videoTranscriptionAPI.delete(id);
      await loadSavedTranscriptions();
      if (selectedTranscription?.id === id) {
        setSelectedTranscription(null);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to delete transcription');
    }
  };

  const stageLabels: Record<string, string> = {
    queued: 'In Queue',
    copy: 'Copying File',
    extract_audio: 'Extracting Audio',
    load_asr: 'Loading ASR Model',
    transcribe: 'Transcribing',
    diarize: 'Diarizing',
    load_align: 'Loading Alignment Model',
    align: 'Aligning',
    assign_speakers: 'Assigning Speakers',
    done: 'Complete',
    error: 'Error',
  };

  // Extract speakers for modal
  const speakers = transcriptionResult ? extractSpeakers(transcriptionResult.text) : [];

  return (
    <div className="min-h-screen bg-dark-charcoal p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-primary-gold mb-6">Video Transcription</h1>

        {/* Tabs */}
        <div className="flex space-x-4 mb-6 border-b border-dark-warm-gray">
          <button
            onClick={() => setActiveTab('new')}
            className={`px-4 py-2 font-semibold ${
              activeTab === 'new'
                ? 'text-primary-gold border-b-2 border-primary-gold'
                : 'text-text-medium hover:text-text-light'
            }`}
          >
            New Transcription
          </button>
          <button
            onClick={() => setActiveTab('saved')}
            className={`px-4 py-2 font-semibold ${
              activeTab === 'saved'
                ? 'text-primary-gold border-b-2 border-primary-gold'
                : 'text-text-medium hover:text-text-light'
            }`}
          >
            Saved Conversations
          </button>
        </div>

        {/* New Transcription Tab */}
        {activeTab === 'new' && (
          <>
            {/* File Selection */}
            <div className="bg-dark-warm-gray rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold text-text-light mb-4">Upload Video</h2>
              
              <div className="mb-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="video-upload"
                />
                <label
                  htmlFor="video-upload"
                  className="btn-primary cursor-pointer inline-block"
                >
                  Select Video File
                </label>
                {selectedFile && (
                  <span className="ml-4 text-text-medium">
                    Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                )}
              </div>

              {/* Transcription Options */}
              {selectedFile && !uploadedFilename && (
                <div className="mt-4 space-y-4 p-4 bg-dark-charcoal rounded">
                  <div>
                    <label className="block text-text-light mb-2">Language</label>
                    <select
                      value={selectedLang}
                      onChange={(e) => setSelectedLang(e.target.value)}
                      className="input-field"
                    >
                      <option value="pt">Portuguese</option>
                      <option value="en">English</option>
                      <option value="auto">Auto-detect</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-text-light mb-2">Model</label>
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="input-field"
                    >
                      <option value="tiny">Tiny (fastest)</option>
                      <option value="base">Base</option>
                      <option value="small">Small (recommended)</option>
                      <option value="medium">Medium</option>
                      <option value="large-v2">Large v2 (best quality)</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="flex items-center text-text-light">
                      <input
                        type="checkbox"
                        checked={diarize}
                        onChange={(e) => setDiarize(e.target.checked)}
                        className="mr-2"
                      />
                      Enable Speaker Diarization
                    </label>
                  </div>
                </div>
              )}

              {selectedFile && !isUploading && !uploadedFilename && (
                <button
                  onClick={handleUpload}
                  className="btn-primary mt-4"
                >
                  Upload Video
                </button>
              )}
              
              {uploadedFilename && !jobId && (
                <div className="mt-4">
                  <p className="text-text-medium mb-4">
                    Video uploaded successfully: <span className="text-primary-gold font-semibold">{uploadedFilename}</span>
                  </p>
                  <button
                    onClick={() => startTranscription(uploadedFilename)}
                    className="btn-primary"
                  >
                    Generate Transcription
                  </button>
                </div>
              )}
            </div>

            {/* Upload Progress */}
            {isUploading && (
              <div className="bg-dark-warm-gray rounded-lg p-6 mb-6">
                <h2 className="text-xl font-semibold text-text-light mb-4">Uploading Video</h2>
                <div className="w-full bg-dark-charcoal rounded-full h-4 mb-2">
                  <div
                    className="bg-primary-gold h-4 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-text-medium">{uploadProgress}% uploaded</p>
              </div>
            )}

            {/* Transcription Progress */}
            {jobId && jobStatus && (
              <div className="bg-dark-warm-gray rounded-lg p-6 mb-6">
                <h2 className="text-xl font-semibold text-text-light mb-4">Transcription Progress</h2>
                
                <div className="mb-4">
                  <div className="flex justify-between text-text-medium mb-2">
                    <span>Status: {stageLabels[currentStage] || jobStatus.status}</span>
                    <span>{currentProgress}%</span>
                  </div>
                  <div className="w-full bg-dark-charcoal rounded-full h-4">
                    <div
                      className="bg-primary-gold h-4 rounded-full transition-all duration-300"
                      style={{ width: `${currentProgress}%` }}
                    />
                  </div>
                </div>

                {currentMessage && (
                  <p className="text-text-medium italic">{currentMessage}</p>
                )}

                {jobStatus.logs && jobStatus.logs.length > 0 && (
                  <div className="mt-4 max-h-48 overflow-y-auto bg-dark-charcoal rounded p-4">
                    <h3 className="text-text-light font-semibold mb-2">Logs:</h3>
                    {jobStatus.logs.map((log, idx) => (
                      <div key={idx} className="text-sm text-text-medium mb-1">
                        <span className="text-primary-gold">[{log.stage}]</span> {log.message} ({log.progress}%)
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Transcription Result */}
            {transcriptionResult && (
              <div className="bg-dark-warm-gray rounded-lg p-6 mb-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-semibold text-text-light">Transcription Result</h2>
                  <div className="flex space-x-2">
                    <button
                      onClick={handleSaveTranscription}
                      className="btn-primary text-sm"
                    >
                      Save Conversation
                    </button>
                    <button
                      onClick={handleReset}
                      className="btn-secondary text-sm"
                    >
                      New Transcription
                    </button>
                  </div>
                </div>
                
                <div className="bg-dark-charcoal rounded p-4 mb-4">
                  <div className="text-sm text-text-medium mb-2">
                    <span className="text-primary-gold">Language:</span> {transcriptionResult.language}
                  </div>
                  <div className="text-sm text-text-medium mb-2">
                    <span className="text-primary-gold">Diarization:</span> {transcriptionResult.diarization ? 'Enabled' : 'Disabled'}
                  </div>
                </div>
                
                <div className="bg-dark-charcoal rounded p-4">
                  <pre className="text-text-light whitespace-pre-wrap font-mono text-sm">
                    {transcriptionResult.text}
                  </pre>
                </div>
                
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(transcriptionResult.text);
                    alert('Text copied to clipboard!');
                  }}
                  className="btn-secondary mt-4"
                >
                  Copy to Clipboard
                </button>
              </div>
            )}
          </>
        )}

        {/* Saved Conversations Tab */}
        {activeTab === 'saved' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* List of saved transcriptions */}
            <div className="lg:col-span-1">
              <div className="bg-dark-warm-gray rounded-lg p-6">
                <h2 className="text-xl font-semibold text-text-light mb-4">Saved Conversations</h2>
                
                {isLoadingSaved ? (
                  <p className="text-text-medium">Loading...</p>
                ) : savedTranscriptions.length === 0 ? (
                  <p className="text-text-medium">No saved conversations yet.</p>
                ) : (
                  <div className="space-y-2">
                    {savedTranscriptions.map((transcription) => (
                      <div
                        key={transcription.id}
                        onClick={() => handleViewTranscription(transcription.id)}
                        className={`p-3 rounded cursor-pointer ${
                          selectedTranscription?.id === transcription.id
                            ? 'bg-primary-gold/20 border border-primary-gold'
                            : 'bg-dark-charcoal hover:bg-dark-charcoal/80'
                        }`}
                      >
                        <div className="text-text-light font-semibold truncate">
                          {transcription.filename}
                        </div>
                        <div className="text-sm text-text-medium">
                          {new Date(transcription.created_at).toLocaleDateString()}
                        </div>
                        {transcription.summary_generating && (
                          <div className="text-xs text-primary-gold mt-1">
                            Generating summary...
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Transcription details */}
            <div className="lg:col-span-2">
              {selectedTranscription ? (
                <div className="bg-dark-warm-gray rounded-lg p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-text-light">
                      {selectedTranscription.filename}
                    </h2>
                    <button
                      onClick={() => handleDeleteTranscription(selectedTranscription.id)}
                      className="btn-secondary text-sm text-red-400"
                    >
                      Delete
                    </button>
                  </div>

                  <div className="bg-dark-charcoal rounded p-4 mb-4">
                    <div className="text-sm text-text-medium mb-2">
                      <span className="text-primary-gold">Language:</span> {selectedTranscription.language}
                    </div>
                    <div className="text-sm text-text-medium mb-2">
                      <span className="text-primary-gold">Created:</span> {new Date(selectedTranscription.created_at).toLocaleString()}
                    </div>
                  </div>

                  {/* Summary */}
                  {selectedTranscription.summary_generating ? (
                    <div className="bg-dark-charcoal rounded p-4 mb-4">
                      <h3 className="text-lg font-semibold text-text-light mb-2">Summary</h3>
                      <p className="text-text-medium">Generating summary...</p>
                    </div>
                  ) : selectedTranscription.summary ? (
                    <div className="bg-dark-charcoal rounded p-4 mb-4">
                      <h3 className="text-lg font-semibold text-text-light mb-2">Summary</h3>
                      <p className="text-text-light whitespace-pre-wrap">{selectedTranscription.summary}</p>
                    </div>
                  ) : null}

                  {/* Transcription Text */}
                  <div className="bg-dark-charcoal rounded p-4">
                    <h3 className="text-lg font-semibold text-text-light mb-2">Transcription</h3>
                    <pre className="text-text-light whitespace-pre-wrap font-mono text-sm">
                      {selectedTranscription.transcription_text}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="bg-dark-warm-gray rounded-lg p-6">
                  <p className="text-text-medium">Select a conversation to view details.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Speaker Identification Modal */}
        {showSpeakerModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-dark-warm-gray rounded-lg p-6 max-w-2xl w-full mx-4">
              <h2 className="text-xl font-semibold text-text-light mb-4">
                Identify Speakers
              </h2>
              <p className="text-text-medium mb-4">
                Enter names for each speaker. Leave blank to keep as {speakers.length > 0 ? speakers[0] : 'User1'}.
              </p>
              
              <div className="space-y-3 mb-4">
                {speakers.map((speaker) => (
                  <div key={speaker}>
                    <label className="block text-text-light mb-1">{speaker}</label>
                    <input
                      type="text"
                      value={speakerMappings[speaker] || ''}
                      onChange={(e) => setSpeakerMappings({
                        ...speakerMappings,
                        [speaker]: e.target.value,
                      })}
                      placeholder={`Enter name for ${speaker}`}
                      className="input-field w-full"
                    />
                  </div>
                ))}
              </div>

              <div className="flex justify-end space-x-2">
                <button
                  onClick={() => {
                    setShowSpeakerModal(false);
                    // If user clicks cancel, save with empty mappings
                    const emptyMappings: Record<string, string> = {};
                    speakers.forEach(speaker => {
                      emptyMappings[speaker] = '';
                    });
                    setSpeakerMappings(emptyMappings);
                  }}
                  className="btn-secondary"
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveWithSpeakers}
                  className="btn-primary"
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving...' : 'Save Conversation'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/30 border border-red-500 rounded-lg p-4 mb-6">
            <p className="text-red-400">{error}</p>
            <button
              onClick={() => setError(null)}
              className="btn-secondary mt-2 text-sm"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoTranscription;
