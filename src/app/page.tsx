'use client';

import React, { useState } from 'react';
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

// Sample data for recently analyzed reports
const recentReports = [
  { 
    id: 1, 
    company: 'Apple Inc.', 
    ticker: 'AAPL', 
    year: '2023',
    status: 'Completed',
    date: 'Feb 26, 2024'
  },
  { 
    id: 2, 
    company: 'Microsoft Corporation', 
    ticker: 'MSFT', 
    year: '2023',
    status: 'Completed',
    date: 'Feb 25, 2024'
  },
  { 
    id: 3, 
    company: 'Tesla, Inc.', 
    ticker: 'TSLA', 
    year: '2022',
    status: 'Processing',
    date: 'Feb 24, 2024'
  }
];

export default function Home() {
  const [companyName, setCompanyName] = useState('');
  const [reportYear, setReportYear] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

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
      
      // Send the request to the backend
      const response = await fetch('/api/reports/upload/', {
        method: 'POST',
        body: formData,
      });
      
      // Check if the response is ok before trying to parse JSON
      if (!response.ok) {
        // Check content type to handle different error formats
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
          // If it's JSON, parse the error details
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to upload report');
        } else {
          // If it's not JSON, use the status text
          throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
        }
      }
      
      // Check content type before parsing JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Server returned an unexpected response format');
      }
      
      // Now safely parse the JSON response
      const data = await response.json();
      console.log('Upload successful:', data);
      
      // Reset form
      setCompanyName('');
      setReportYear('');
      setSelectedFile(null);
      setSuccess(true);
      
      // Reload the page after 2 seconds to show the new report
      setTimeout(() => {
        window.location.reload();
      }, 2000);
      
    } catch (err) {
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSuccess(false);
    setError(null);
  };

  return (
    <PageLayout>
      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Annual Report Analyzer
        </Typography>
        <Typography variant="h6" color="text.secondary">
          Upload company annual reports and get AI-powered insights, financial metrics,
          and business outlook analysis.
        </Typography>
      </Box>

      <Grid container spacing={4}>
        {/* Upload Section */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 4 }}>
            <Typography variant="h5" component="h2" gutterBottom>
              Upload Report
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Upload a company annual report in PDF format
            </Typography>
            
            <Box component="form" sx={{ mb: 3 }} encType="multipart/form-data">
              <TextField
                fullWidth
                label="Company Name"
                variant="outlined"
                placeholder="e.g. Apple Inc."
                value={companyName}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCompanyName(e.target.value)}
                sx={{ mb: 2 }}
              />
              
              <TextField
                fullWidth
                label="Report Year"
                variant="outlined"
                placeholder="e.g. 2023"
                value={reportYear}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setReportYear(e.target.value)}
                sx={{ mb: 3 }}
              />
              
              <Box 
                sx={{ 
                  border: '2px dashed #ccc', 
                  borderRadius: 2, 
                  p: 3, 
                  textAlign: 'center',
                  mb: 3,
                  cursor: 'pointer',
                  '&:hover': {
                    borderColor: 'primary.main',
                  }
                }}
                onClick={() => document.getElementById('file-upload')?.click()}
              >
                <input
                  type="file"
                  id="file-upload"
                  accept=".pdf"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                <CloudUploadIcon fontSize="large" color="primary" />
                <Typography variant="body1" sx={{ mt: 1 }}>
                  {selectedFile ? selectedFile.name : 'Click to upload or drag and drop'}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  PDF (MAX. 50MB)
                </Typography>
              </Box>
              
              <Button 
                variant="contained" 
                fullWidth 
                size="large"
                startIcon={loading ? <CircularProgress size={24} color="inherit" /> : <CloudUploadIcon />}
                onClick={handleUpload}
                disabled={!selectedFile || !companyName || !reportYear || loading}
              >
                {loading ? 'Uploading...' : 'Upload and Analyze'}
              </Button>
            </Box>
          </Paper>
        </Grid>
        
        {/* Navigation and Recent Reports */}
        <Grid item xs={12} md={6}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Paper sx={{ p: 4 }}>
                <Typography variant="h5" component="h2" gutterBottom>
                  Dashboard
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  View analyzed reports and key metrics
                </Typography>
                
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  <Button 
                    variant="contained" 
                    component={Link} 
                    href="/dashboard"
                    size="large"
                    fullWidth
                    sx={{ maxWidth: 300 }}
                  >
                    View Dashboard
                  </Button>
                </Box>
              </Paper>
            </Grid>
            
            <Grid item xs={12}>
              <Paper sx={{ p: 4 }}>
                <Typography variant="h5" component="h2" gutterBottom>
                  Search Reports
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Find and compare company reports
                </Typography>
                
                <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                  <Button 
                    variant="outlined" 
                    component={Link} 
                    href="/search"
                    size="large"
                    fullWidth
                    sx={{ maxWidth: 300 }}
                  >
                    Search Reports
                  </Button>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Grid>
        
        {/* Recently Analyzed Reports */}
        <Grid item xs={12}>
          <Typography variant="h5" component="h2" gutterBottom>
            Recently Analyzed Reports
          </Typography>
          
          <Grid container spacing={3}>
            {recentReports.map((report) => (
              <Grid item xs={12} sm={6} md={4} key={report.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <FileIcon color="primary" sx={{ mr: 1 }} />
                      <Typography variant="h6" component="div">
                        {report.company}
                      </Typography>
                    </Box>
                    
                    <Typography color="text.secondary" gutterBottom>
                      Annual Report {report.year}
                    </Typography>
                    
                    <Divider sx={{ my: 1.5 }} />
                    
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
                      <Chip 
                        label={report.status} 
                        color={report.status === 'Completed' ? 'success' : 'warning'} 
                        size="small" 
                      />
                      <Typography variant="body2" color="text.secondary">
                        {report.date}
                      </Typography>
                    </Box>
                    
                    <Box sx={{ mt: 2 }}>
                      <Button 
                        variant="outlined" 
                        size="small" 
                        component={Link}
                        href={`/reports/${report.id}`}
                        fullWidth
                      >
                        View Analysis
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>

      {/* Snackbar for success or error messages */}
      <Snackbar
        open={success || error}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
      >
        <Alert onClose={handleCloseSnackbar} severity={success ? "success" : "error"}>
          {success ? 'Report uploaded successfully!' : error}
        </Alert>
      </Snackbar>
    </PageLayout>
  );
}
