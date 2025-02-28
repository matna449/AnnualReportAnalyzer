'use client';

import React, { useState } from 'react';
import { 
  Typography, 
  Paper,
  Grid,
  TextField,
  Button,
  Box,
  CircularProgress,
  Alert,
  Divider,
  Card,
  CardContent,
  CardActions,
  Chip
} from '@mui/material';
import { 
  Search as SearchIcon,
  Business as BusinessIcon,
  Description as DescriptionIcon,
  Visibility as VisibilityIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import Link from 'next/link';
import PageLayout from '@/components/PageLayout';
import axios from 'axios';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useState({
    company_name: '',
    ticker: '',
    year: '',
    sector: ''
  });
  
  const [searchResults, setSearchResults] = useState<{
    companies: any[];
    reports: any[];
  }>({
    companies: [],
    reports: []
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setSearchParams({
      ...searchParams,
      [name]: value
    });
  };
  
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check if at least one search parameter is provided
    const hasSearchParam = Object.values(searchParams).some(param => param.trim() !== '');
    
    if (!hasSearchParam) {
      setError('Please enter at least one search parameter');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('/api/reports/search/', searchParams);
      setSearchResults(response.data);
      setSearched(true);
    } catch (err) {
      console.error('Error searching reports:', err);
      setError('Failed to search reports. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleReset = () => {
    setSearchParams({
      company_name: '',
      ticker: '',
      year: '',
      sector: ''
    });
    setSearchResults({
      companies: [],
      reports: []
    });
    setSearched(false);
    setError(null);
  };
  
  return (
    <PageLayout>
      <Typography variant="h4" component="h1" gutterBottom>
        Search Reports
      </Typography>
      
      <Paper sx={{ p: 4, mb: 4 }}>
        <form onSubmit={handleSearch}>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Company Name"
                name="company_name"
                value={searchParams.company_name}
                onChange={handleInputChange}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Ticker Symbol"
                name="ticker"
                value={searchParams.ticker}
                onChange={handleInputChange}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Year"
                name="year"
                value={searchParams.year}
                onChange={handleInputChange}
                variant="outlined"
                placeholder="e.g. 2023"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Sector"
                name="sector"
                value={searchParams.sector}
                onChange={handleInputChange}
                variant="outlined"
                placeholder="e.g. Technology"
              />
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
                  disabled={loading}
                >
                  Search
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<ClearIcon />}
                  onClick={handleReset}
                  disabled={loading}
                >
                  Reset
                </Button>
              </Box>
            </Grid>
          </Grid>
        </form>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}
      
      {searched && !loading && (
        <>
          {searchResults.companies.length === 0 && searchResults.reports.length === 0 ? (
            <Alert severity="info" sx={{ mb: 4 }}>
              No results found for your search criteria.
            </Alert>
          ) : (
            <>
              {/* Companies Results */}
              {searchResults.companies.length > 0 && (
                <Box sx={{ mb: 4 }}>
                  <Typography variant="h5" gutterBottom>
                    Companies ({searchResults.companies.length})
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  
                  <Grid container spacing={3}>
                    {searchResults.companies.map(company => (
                      <Grid item xs={12} sm={6} md={4} key={company.id}>
                        <Card>
                          <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                              <BusinessIcon sx={{ mr: 1, color: 'primary.main' }} />
                              <Typography variant="h6" component="div">
                                {company.name}
                              </Typography>
                            </Box>
                            
                            {company.ticker && (
                              <Typography variant="body2" color="text.secondary" gutterBottom>
                                Ticker: {company.ticker}
                              </Typography>
                            )}
                            
                            {company.sector && (
                              <Typography variant="body2" color="text.secondary" gutterBottom>
                                Sector: {company.sector}
                              </Typography>
                            )}
                            
                            <Typography variant="body2" color="text.secondary">
                              Reports: {company.reports?.length || 0}
                            </Typography>
                          </CardContent>
                          <CardActions>
                            <Link href={`/reports/${company.id}`} passHref>
                              <Button 
                                size="small" 
                                startIcon={<VisibilityIcon />}
                                component="a"
                              >
                                View Reports
                              </Button>
                            </Link>
                          </CardActions>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              )}
              
              {/* Reports Results */}
              {searchResults.reports.length > 0 && (
                <Box>
                  <Typography variant="h5" gutterBottom>
                    Reports ({searchResults.reports.length})
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  
                  <Grid container spacing={3}>
                    {searchResults.reports.map(report => (
                      <Grid item xs={12} sm={6} md={4} key={report.id}>
                        <Card>
                          <CardContent>
                            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                              <DescriptionIcon sx={{ mr: 1, color: 'primary.main' }} />
                              <Typography variant="h6" component="div">
                                {report.company.name} ({report.year})
                              </Typography>
                            </Box>
                            
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              File: {report.file_name}
                            </Typography>
                            
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              Uploaded: {new Date(report.upload_date).toLocaleDateString()}
                            </Typography>
                            
                            <Box sx={{ mt: 1 }}>
                              <Chip 
                                label={report.processing_status} 
                                color={
                                  report.processing_status === 'completed' 
                                    ? 'success' 
                                    : report.processing_status === 'processing' 
                                      ? 'warning' 
                                      : report.processing_status === 'pending'
                                        ? 'info'
                                        : 'error'
                                }
                                size="small"
                              />
                            </Box>
                          </CardContent>
                          <CardActions>
                            <Link href={`/reports/${report.id}`} passHref>
                              <Button 
                                size="small" 
                                startIcon={<VisibilityIcon />}
                                component="a"
                              >
                                View Analysis
                              </Button>
                            </Link>
                          </CardActions>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              )}
            </>
          )}
        </>
      )}
    </PageLayout>
  );
} 