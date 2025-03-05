'use client';

import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Box, 
  Paper, 
  Grid, 
  TextField, 
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  CircularProgress,
  Alert,
  Snackbar,
  CardActions,
  List,
  ListItem,
  ListItemText,
  LinearProgress
} from '@mui/material';
import { 
  CloudUpload as CloudUploadIcon,
  InsertDriveFile as FileIcon,
  Article as ArticleIcon,
  Check as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import Link from 'next/link';
import PageLayout from '@/components/PageLayout';
import ClientOnlyPortal from '@/components/ClientOnlyPortal';
import LogViewer from '@/components/LogViewer';
import { shouldShowLogs } from '@/utils/featureFlags';
import DebugContainer from '@/components/DebugContainer';

// Define report type
interface Report {
  id: number;
  company: string;
  ticker: string;
  year: string;
  status: string;
  date: string;
}

export default function Home() {
  const [companyName, setCompanyName] = useState('');
  const [reportYear, setReportYear] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [recentReports, setRecentReports] = useState<Report[]>([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [reportError, setReportError] = useState<string | null>(null);
  const [uploadedReportId, setUploadedReportId] = useState<number | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);
  const [shouldBlockNavigation, setShouldBlockNavigation] = useState(false);
  const [processingStep, setProcessingStep] = useState<string | null>(null);

  // Fetch recent reports on component mount
  useEffect(() => {
    fetchRecentReports();
  }, []);

  const fetchRecentReports = async () => {
    try {
      setLoadingReports(true);
      setReportError(null);
      
      // Log the API request
      console.log('Fetching recent reports from /api/dashboard/recent-reports');
      
      const response = await fetch('/api/dashboard/recent-reports');
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`API error (${response.status}): ${errorText}`);
        throw new Error(`Failed to fetch recent reports: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Received data:', data);
      
      // Transform the data to match our Report interface
      const reports: Report[] = data.map((report: any) => ({
        id: report.id,
        company: report.company_name,
        ticker: report.ticker || 'N/A',
        year: report.year,
        status: report.processing_status,
        date: new Date(report.upload_date).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        })
      }));
      
      setRecentReports(reports);
    } catch (error) {
      console.error('Error fetching recent reports:', error);
      setReportError(error instanceof Error ? error.message : 'Failed to fetch recent reports. Please try again later.');
    } finally {
      setLoadingReports(false);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !companyName || !reportYear) return;
    
    setLoading(true);
    setError(null);
    setShouldBlockNavigation(true);
    setProcessingStep("uploading");
    
    try {
      // Create FormData object
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('company_name', companyName);
      formData.append('year', reportYear);
      
      console.log('Uploading file:', selectedFile.name, 'Size:', selectedFile.size, 'Type:', selectedFile.type);
      console.log('Request URL:', '/api/reports/upload');
      
      // Send the request to the backend
      const response = await fetch('/api/reports/upload', {
        method: 'POST',
        body: formData,
      });
      
      console.log('Response status:', response.status, response.statusText);
      
      // Log headers in a way that works with all TypeScript targets
      const headers: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        headers[key] = value;
      });
      console.log('Response headers:', headers);
      
      // Check if the response is ok before trying to parse JSON
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response body:', errorText);
        setShouldBlockNavigation(false);
        throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Response data:', data);
      
      setSuccess(true);
      setCompanyName('');
      setReportYear('');
      setSelectedFile(null);
      
      // Set the uploaded report ID and start polling for status
      if (data && data.report_id) {
        setUploadedReportId(data.report_id);
        setProcessingStep("processing");
        startPollingReportStatus(data.report_id);
      }
      
      // Refresh the recent reports list
      fetchRecentReports();
      
    } catch (error) {
      console.error('Error uploading file:', error);
      setError(error instanceof Error ? error.message : 'An unknown error occurred');
      setShouldBlockNavigation(false);
      setProcessingStep(null);
    } finally {
      setLoading(false);
    }
  };

  // Function to poll for report status
  const startPollingReportStatus = (reportId: number) => {
    // Clear any existing interval
    if (pollInterval) {
      clearInterval(pollInterval);
    }
    
    // Start a new polling interval
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/reports/${reportId}/status`);
        if (!response.ok) {
          throw new Error(`Failed to fetch status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Report status update:', data);
        
        if (data && data.status) {
          setProcessingStatus(data.status);
          
          // Update processing step based on status
          if (data.status === 'pending') {
            setProcessingStep('queued');
          } else if (data.status === 'processing') {
            setProcessingStep('analyzing');
          } else if (data.status === 'completed') {
            setProcessingStep('completed');
            setShouldBlockNavigation(false);
            // Stop polling if completed
            clearInterval(interval);
            setPollInterval(null);
            
            // Refresh the recent reports list
            fetchRecentReports();
          } else if (data.status.includes('error')) {
            setProcessingStep('error');
            setShouldBlockNavigation(false);
            // Stop polling on error
            clearInterval(interval);
            setPollInterval(null);
            setError(`Processing error: ${data.status}`);
          }
        }
      } catch (error) {
        console.error('Error polling for status:', error);
        // Don't stop polling on network errors, let it continue trying
      }
    }, 3000); // Poll every 3 seconds
    
    setPollInterval(interval);
    
    // Clean up the interval when component unmounts
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  };

  // Effect to handle clean up of polling interval
  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

  // Add an effect to warn user when trying to navigate away during processing
  useEffect(() => {
    if (shouldBlockNavigation) {
      const handleBeforeUnload = (e: BeforeUnloadEvent) => {
        const message = "Analysis is still in progress. Are you sure you want to leave?";
        e.preventDefault();
        e.returnValue = message;
        return message;
      };
      
      window.addEventListener('beforeunload', handleBeforeUnload);
      
      return () => {
        window.removeEventListener('beforeunload', handleBeforeUnload);
      };
    }
  }, [shouldBlockNavigation]);

  const handleCloseSnackbar = () => {
    setSuccess(false);
    setError(null);
  };

  // Function to get status chip color
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'processing':
      case 'processing_enhanced_analysis':
        return 'warning';
      case 'pending':
        return 'info';
      case 'failed':
      case 'error':
      case 'error_enhanced_analysis':
        return 'error';
      default:
        return 'default';
    }
  };

  // Function to get human-readable status
  const getReadableStatus = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'Completed';
      case 'processing':
        return 'Processing';
      case 'processing_enhanced_analysis':
        return 'Enhanced Analysis';
      case 'pending':
        return 'Pending';
      case 'failed':
        return 'Failed';
      case 'error':
        return 'Error';
      case 'error_enhanced_analysis':
        return 'Analysis Error';
      default:
        return status;
    }
  };

  // Get progress step display info
  const getProcessingStepInfo = () => {
    switch (processingStep) {
      case 'uploading':
        return {
          label: 'Uploading PDF...',
          progress: 20,
          description: 'Your PDF is being uploaded to our servers.'
        };
      case 'queued':
        return {
          label: 'In Queue',
          progress: 40,
          description: 'Your report is queued for analysis.'
        };
      case 'processing':
      case 'analyzing':
        return {
          label: 'Analyzing Content',
          progress: 60,
          description: 'Extracting and analyzing text from your PDF.'
        };
      case 'completed':
        return {
          label: 'Analysis Complete',
          progress: 100,
          description: 'Your report has been fully analyzed and is ready to view.'
        };
      case 'error':
        return {
          label: 'Error',
          progress: 100,
          description: 'An error occurred during analysis. Please try again.'
        };
      default:
        return {
          label: 'Ready',
          progress: 0,
          description: 'Select a PDF file to upload.'
        };
    }
  };

  // Get processing step info
  const stepInfo = getProcessingStepInfo();

  return (
    <PageLayout>
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Annual Report Analyzer
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" paragraph>
          Upload an annual report PDF to extract financial data and generate insights
        </Typography>
        
        {/* Upload Section */}
        <Paper elevation={0} sx={{ p: 4, mb: 4, borderRadius: 2 }}>
          <Typography variant="h5" gutterBottom>
            Upload Annual Report
          </Typography>
          
          <Grid container spacing={3} component="form" onSubmit={(e) => { e.preventDefault(); handleUpload(); }}>
            <Grid item xs={12} md={6}>
              <ClientOnlyPortal>
                <TextField
                  label="Company Name"
                  fullWidth
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  required
                  margin="normal"
                  error={!!error && !companyName}
                  helperText={error && !companyName ? "Company name is required" : ""}
                  disabled={loading || shouldBlockNavigation}
                />
              </ClientOnlyPortal>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <ClientOnlyPortal>
                <TextField
                  label="Report Year"
                  fullWidth
                  type="number"
                  value={reportYear}
                  onChange={(e) => setReportYear(e.target.value)}
                  required
                  margin="normal"
                  error={!!error && !reportYear}
                  helperText={error && !reportYear ? "Report year is required" : ""}
                  inputProps={{ min: 1900, max: new Date().getFullYear() }}
                  disabled={loading || shouldBlockNavigation}
                />
              </ClientOnlyPortal>
            </Grid>
            
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mt: 2 }}>
                <input
                  accept="application/pdf"
                  style={{ display: 'none' }}
                  id="upload-file"
                  type="file"
                  onChange={handleFileChange}
                  disabled={loading || shouldBlockNavigation}
                />
                <label htmlFor="upload-file">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<CloudUploadIcon />}
                    sx={{ mb: 2 }}
                    disabled={loading || shouldBlockNavigation}
                  >
                    Select PDF File
                  </Button>
                </label>
                
                {selectedFile && (
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    Selected: {selectedFile.name}
                  </Typography>
                )}
                
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleUpload}
                  disabled={loading || shouldBlockNavigation || !selectedFile || !companyName || !reportYear}
                  startIcon={loading ? <CircularProgress size={24} color="inherit" /> : null}
                >
                  {loading ? 'Uploading...' : 'Upload Report'}
                </Button>
              </Box>
            </Grid>
          </Grid>
          
          {shouldBlockNavigation && (
            <Box sx={{ mt: 4, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
              <Typography variant="h6" gutterBottom>
                {stepInfo.label}
              </Typography>
              
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Box sx={{ width: '100%', mr: 1 }}>
                  <LinearProgress variant="determinate" value={stepInfo.progress} />
                </Box>
                <Box sx={{ minWidth: 35 }}>
                  <Typography variant="body2" color="text.secondary">{`${Math.round(stepInfo.progress)}%`}</Typography>
                </Box>
              </Box>
              
              <Typography variant="body2" color="text.secondary">
                {stepInfo.description}
              </Typography>
              
              <Typography variant="body2" color="error" sx={{ mt: 2, fontWeight: 'bold' }}>
                Please do not navigate away from this page until processing is complete.
              </Typography>
              
              {uploadedReportId && shouldShowLogs() && (
                <Box sx={{ mt: 2 }}>
                  <LogViewer 
                    reportId={uploadedReportId} 
                    height={300} 
                    label="Processing Logs" 
                  />
                </Box>
              )}
              
              {/* Example of using DebugContainer for other debugging elements */}
              <DebugContainer title="Upload Process Debug Info">
                <Typography variant="body2">
                  Report ID: {uploadedReportId || 'None'}
                </Typography>
                <Typography variant="body2">
                  Processing Status: {processingStatus || 'Not started'}
                </Typography>
                <Typography variant="body2">
                  Current Step: {processingStep || 'None'}
                </Typography>
              </DebugContainer>
              
            </Box>
          )}
        </Paper>
        
        <Typography variant="h6" gutterBottom>
          Recently Analyzed Reports
        </Typography>
        
        {loadingReports ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : recentReports.length > 0 ? (
          <Grid container spacing={2}>
            {recentReports.map((report) => (
              <Grid item xs={12} sm={6} md={4} key={report.id}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" component="div">
                      {report.company}
                    </Typography>
                    <Typography color="text.secondary" gutterBottom>
                      {report.ticker} | {report.year}
                    </Typography>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
                      <Chip 
                        label={getReadableStatus(report.status)} 
                        color={getStatusColor(report.status) as any}
                        size="small" 
                      />
                      <Typography variant="body2" color="text.secondary">
                        {report.date}
                      </Typography>
                    </Box>
                    <Divider sx={{ my: 2 }} />
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <Link href={`/reports/${report.id}`} passHref>
                        <Button size="small" color="primary" disabled={shouldBlockNavigation && uploadedReportId === report.id}>
                          View Analysis
                        </Button>
                      </Link>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No reports have been analyzed yet. Upload an annual report to get started.
            </Typography>
          </Paper>
        )}
      </Box>
      
      <Snackbar open={!!error} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
      
      <Snackbar open={success} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity="success" sx={{ width: '100%' }}>
          Report uploaded successfully! Analysis is in progress.
        </Alert>
      </Snackbar>
    </PageLayout>
  );
}
