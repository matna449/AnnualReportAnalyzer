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
  Snackbar
} from '@mui/material';
import { 
  CloudUpload as CloudUploadIcon,
  InsertDriveFile as FileIcon
} from '@mui/icons-material';
import Link from 'next/link';
import PageLayout from '@/components/PageLayout';

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

  // Fetch recent reports on component mount
  useEffect(() => {
    fetchRecentReports();
  }, []);

  const fetchRecentReports = async () => {
    try {
      setLoadingReports(true);
      const response = await fetch('/api/reports/recent');
      
      if (!response.ok) {
        throw new Error('Failed to fetch recent reports');
      }
      
      const data = await response.json();
      
      // Transform the data to match our Report interface
      const reports: Report[] = data.reports.map((report: any) => ({
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
      // If we can't fetch reports, use empty array
      setRecentReports([]);
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
        throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Response data:', data);
      
      setSuccess(true);
      setCompanyName('');
      setReportYear('');
      setSelectedFile(null);
      
      // Refresh the recent reports list
      fetchRecentReports();
      
    } catch (error) {
      console.error('Error uploading file:', error);
      setError(error instanceof Error ? error.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

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
        return 'warning';
      case 'pending':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <PageLayout>
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Annual Report Analyzer
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" paragraph>
          Upload an annual report PDF to extract financial data and generate insights
        </Typography>
        
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Upload Annual Report
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Company Name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                margin="normal"
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Report Year"
                value={reportYear}
                onChange={(e) => setReportYear(e.target.value)}
                margin="normal"
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box sx={{ mt: 3 }}>
                <input
                  accept="application/pdf"
                  style={{ display: 'none' }}
                  id="raised-button-file"
                  type="file"
                  onChange={handleFileChange}
                />
                <label htmlFor="raised-button-file">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<CloudUploadIcon />}
                    sx={{ mr: 2 }}
                  >
                    Select PDF
                  </Button>
                </label>
                {selectedFile && (
                  <Typography variant="body2" component="span">
                    {selectedFile.name}
                  </Typography>
                )}
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleUpload}
                disabled={!selectedFile || !companyName || !reportYear || loading}
                startIcon={loading ? <CircularProgress size={24} color="inherit" /> : <FileIcon />}
              >
                {loading ? 'Uploading...' : 'Upload and Analyze'}
              </Button>
            </Grid>
          </Grid>
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
                        label={report.status} 
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
                        <Button size="small" color="primary">
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
