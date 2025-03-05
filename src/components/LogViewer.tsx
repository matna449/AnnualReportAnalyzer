'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  List,
  ListItem,
  ListItemText,
  Chip,
  Divider,
  IconButton,
  CircularProgress,
  Switch,
  FormControlLabel,
  Button
} from '@mui/material';
import { 
  Clear as ClearIcon, 
  FilterList as FilterIcon,
  KeyboardArrowDown as ScrollDownIcon
} from '@mui/icons-material';
import { shouldShowLogs } from '@/utils/featureFlags';

interface LogEntry {
  timestamp: number;
  level: string;
  message: string;
  logger: string;
  pipeline: boolean;
}

interface LogViewerProps {
  reportId?: number; // Optional report ID to filter logs by
  maxLogs?: number; // Maximum number of logs to display
  autoScroll?: boolean; // Whether to automatically scroll to the bottom
  height?: string | number; // Height of the log viewer
  label?: string; // Label for the log viewer
  isVisible?: boolean; // Whether this component should be visible (for developer mode)
}

const LogViewer: React.FC<LogViewerProps> = ({
  reportId,
  maxLogs = 100,
  autoScroll = true,
  height = 300,
  label = "Processing Logs",
  isVisible = shouldShowLogs() // Use our feature flag utility
}) => {
  // Exit early if not visible
  if (!isVisible) return null;
  
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isAutoScrolling, setIsAutoScrolling] = useState(autoScroll);
  const [showOnlyPipeline, setShowOnlyPipeline] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  
  useEffect(() => {
    // Connect to the log stream
    const connectToLogStream = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      
      const eventSource = new EventSource('/api/logs/stream');
      eventSourceRef.current = eventSource;
      
      eventSource.onopen = () => {
        console.log('Connected to log stream');
        setIsConnected(true);
      };
      
      eventSource.onmessage = (event) => {
        try {
          const logEntry: LogEntry = JSON.parse(event.data);
          
          // Only add logs that are relevant to the current report if a report ID is provided
          if (reportId && !logEntry.message.includes(`Report ID: ${reportId}`)) {
            return;
          }
          
          setLogs(prevLogs => {
            const newLogs = [...prevLogs, logEntry];
            // Limit the number of logs to avoid memory issues
            return newLogs.slice(-maxLogs);
          });
          
          // Scroll to bottom if auto-scrolling is enabled
          if (isAutoScrolling) {
            scrollToBottom();
          }
        } catch (error) {
          console.error('Error parsing log entry', error);
        }
      };
      
      eventSource.onerror = (error) => {
        console.error('Log stream error:', error);
        setIsConnected(false);
        
        // Try to reconnect after a delay
        setTimeout(() => {
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            connectToLogStream();
          }
        }, 5000);
      };
    };
    
    connectToLogStream();
    
    // Clean up the event source when component unmounts
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [reportId, maxLogs]);
  
  // Effect to handle auto-scrolling
  useEffect(() => {
    if (isAutoScrolling) {
      scrollToBottom();
    }
  }, [logs, isAutoScrolling]);
  
  const scrollToBottom = () => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const clearLogs = () => {
    setLogs([]);
  };
  
  // Get log level color
  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      case 'debug':
        return 'default';
      default:
        return 'default';
    }
  };
  
  // Format timestamp to readable format
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };
  
  // Filter logs based on pipeline setting
  const filteredLogs = showOnlyPipeline 
    ? logs.filter(log => log.pipeline) 
    : logs;

  return (
    <Paper elevation={1} sx={{ height, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ 
        p: 1, 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        borderBottom: '1px solid rgba(0, 0, 0, 0.12)'
      }}>
        <Typography variant="subtitle1" component="div" fontWeight="medium">
          {label}
          {!isConnected && (
            <CircularProgress size={16} sx={{ ml: 1, verticalAlign: 'middle' }} />
          )}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={showOnlyPipeline}
                onChange={(e) => setShowOnlyPipeline(e.target.checked)}
              />
            }
            label={<Typography variant="caption">Pipeline only</Typography>}
            sx={{ mr: 1 }}
          />
          
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={isAutoScrolling}
                onChange={(e) => setIsAutoScrolling(e.target.checked)}
              />
            }
            label={<Typography variant="caption">Auto-scroll</Typography>}
            sx={{ mr: 1 }}
          />
          
          <IconButton size="small" onClick={clearLogs} title="Clear logs">
            <ClearIcon fontSize="small" />
          </IconButton>
          
          <IconButton 
            size="small" 
            onClick={scrollToBottom} 
            title="Scroll to bottom"
            sx={{ ml: 1 }}
            disabled={isAutoScrolling}
          >
            <ScrollDownIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>
      
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto', 
        fontFamily: 'monospace', 
        fontSize: '0.875rem',
        p: 1,
        backgroundColor: '#f5f5f5'
      }}>
        {filteredLogs.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
            No logs available. Processing events will appear here.
          </Typography>
        ) : (
          filteredLogs.map((log, index) => (
            <Box 
              key={index} 
              sx={{ 
                mb: 0.5, 
                p: 0.5,
                borderRadius: 1,
                backgroundColor: log.level.toLowerCase() === 'error' ? 'rgba(255, 0, 0, 0.05)' : 'transparent'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                <Chip 
                  label={log.level} 
                  size="small" 
                  color={getLevelColor(log.level) as any}
                  sx={{ 
                    height: 20, 
                    fontSize: '0.7rem', 
                    mr: 1,
                    minWidth: 50
                  }}
                />
                <Typography 
                  variant="caption" 
                  color="text.secondary" 
                  sx={{ mr: 1, minWidth: 70 }}
                >
                  {formatTimestamp(log.timestamp)}
                </Typography>
                <Typography 
                  variant="body2" 
                  component="pre" 
                  sx={{ 
                    m: 0, 
                    wordBreak: 'break-word',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    flexGrow: 1
                  }}
                >
                  {log.message}
                </Typography>
              </Box>
            </Box>
          ))
        )}
        <div ref={logEndRef} />
      </Box>
    </Paper>
  );
};

export default LogViewer; 