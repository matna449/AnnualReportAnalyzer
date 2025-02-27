'use client';

import React, { useState } from 'react';
import { 
  Typography, 
  Box, 
  Grid, 
  Paper,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import Link from 'next/link';
import PageLayout from '@/components/PageLayout';

export default function SearchPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchPerformed, setSearchPerformed] = useState(false);
  
  // Search form state
  const [companyName, setCompanyName] = useState('');
  const [year, setYear] = useState('');
  const [sector, setSector] = useState('');
  const [status, setStatus] = useState('');
  
  // Sample sectors for dropdown
  const sectors = [
    'Technology',
    'Healthcare',
    'Finance',
    'Energy',
    'Consumer Goods',
    'Telecommunications',
    'Manufacturing'
  ];
  
  // Sample statuses for dropdown
  const statuses = [
    'Completed',
    'Processing',
    'Failed'
  ];
  
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    setLoading(true);
    setError(null);
    setSearchPerformed(true);
    
    try {
      // Build search params
      const searchParams = new URLSearchParams();
      if (companyName) searchParams.append('company_name', companyName);
      if (year) searchParams.append('year', year);
      if (sector) searchParams.append('sector', sector);
      if (status) searchParams.append('status', status);
      
      // Make API request
      const response = await fetch(`/api/reports/search/?${searchParams.toString()}`);
      
      if (!response.ok) {
        throw new Error('Search failed');
      }
      
      const data = await response.json();
      setSearchResults(data);
    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'An error occurred during search');
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };
  
  const handleReset = () => {
    setCompanyName('');
    setYear('');
    setSector('');
    setStatus('');
    setSearchResults([]);
    setSearchPerformed(false);
    setError(null);
  };
  
  return (
    <PageLayout>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Search Reports
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Find and compare annual reports
        </Typography>
      </Box>
      
      {/* Search Form */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Box component="form" onSubmit={handleSearch}>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Company Name"
                variant="outlined"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Year"
                variant="outlined"
                type="number"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                inputProps={{ min: 1900, max: new Date().getFullYear() + 1 }}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Sector</InputLabel>
                <Select
                  value={sector}
                  label="Sector"
                  onChange={(e) => setSector(e.target.value)}
                >
                  <MenuItem value="">All Sectors</MenuItem>
                  {sectors.map((s) => (
                    <MenuItem key={s} value={s}>{s}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={status}
                  label="Status"
                  onChange={(e) => setStatus(e.target.value)}
                >
                  <MenuItem value="">All Statuses</MenuItem>
                  {statuses.map((s) => (
                    <MenuItem key={s} value={s}>{s}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button 
                  variant="outlined" 
                  onClick={handleReset}
                >
                  Reset
                </Button>
                <Button 
                  type="submit"
                  variant="contained" 
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
                  disabled={loading}
                >
                  Search
                </Button>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </Paper>
      
      {/* Search Results */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ my: 2 }}>
          {error}
        </Alert>
      ) : searchPerformed ? (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Search Results ({searchResults.length})
          </Typography>
          
          {searchResults.length === 0 ? (
            <Typography variant="body1" color="text.secondary" sx={{ my: 4, textAlign: 'center' }}>
              No reports found matching your search criteria.
            </Typography>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Company</TableCell>
                    <TableCell>Year</TableCell>
                    <TableCell>Upload Date</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {searchResults.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell>{report.company_name}</TableCell>
                      <TableCell>{report.year}</TableCell>
                      <TableCell>{new Date(report.upload_date).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Chip 
                          label={report.processing_status} 
                          color={report.processing_status === 'Completed' ? 'success' : 
                                 report.processing_status === 'Processing' ? 'warning' : 'error'} 
                          size="small" 
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button 
                          component={Link}
                          href={`/reports/${report.id}`}
                          size="small"
                          variant="outlined"
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      ) : null}
    </PageLayout>
  );
} 