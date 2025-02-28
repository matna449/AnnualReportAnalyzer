'use client';

import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Box,
  Chip,
  CircularProgress,
  Alert,
  FormGroup,
  FormControlLabel,
  Checkbox
} from '@mui/material';
import PageLayout from '@/components/PageLayout';
import FinancialPerformanceChart from '@/components/FinancialPerformanceChart';
import axios from 'axios';

export default function ComparePage() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompanies, setSelectedCompanies] = useState<number[]>([]);
  const [availableMetrics, setAvailableMetrics] = useState<string[]>([
    'revenue', 'netIncome', 'operatingIncome', 'grossMargin', 'operatingMargin', 'netMargin',
    'eps', 'totalAssets', 'totalLiabilities', 'cashFlow', 'rnd'
  ]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['revenue']);
  const [comparisonData, setComparisonData] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');

  // Fetch companies on component mount
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const response = await axios.get('/api/companies/');
        setCompanies(response.data);
      } catch (err) {
        console.error('Error fetching companies:', err);
        setError('Failed to load companies. Please try again later.');
      }
    };

    fetchCompanies();
  }, []);

  // Handle company selection
  const handleCompanyChange = (event: React.ChangeEvent<{ value: unknown }>) => {
    const companyId = event.target.value as number;
    
    // Add company if not already selected
    if (!selectedCompanies.includes(companyId)) {
      setSelectedCompanies([...selectedCompanies, companyId]);
    }
  };

  // Remove a company from comparison
  const handleRemoveCompany = (companyId: number) => {
    setSelectedCompanies(selectedCompanies.filter(id => id !== companyId));
  };

  // Handle metric selection
  const handleMetricChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const metric = event.target.name;
    
    if (event.target.checked) {
      setSelectedMetrics([...selectedMetrics, metric]);
    } else {
      setSelectedMetrics(selectedMetrics.filter(m => m !== metric));
    }
  };

  // Toggle chart type
  const handleChartTypeChange = () => {
    setChartType(chartType === 'line' ? 'bar' : 'line');
  };

  // Fetch comparison data
  const handleCompare = async () => {
    if (selectedCompanies.length === 0) {
      setError('Please select at least one company to compare');
      return;
    }

    if (selectedMetrics.length === 0) {
      setError('Please select at least one metric to compare');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Fetch metrics for each selected company
      const metricsPromises = selectedCompanies.map(companyId => 
        axios.get(`/api/companies/${companyId}/metrics`, {
          params: { metric_names: selectedMetrics.join(',') }
        })
      );
      
      const responses = await Promise.all(metricsPromises);
      
      // Process the data for the chart
      const processedData = processComparisonData(responses, selectedCompanies);
      setComparisonData(processedData);
    } catch (err) {
      console.error('Error fetching comparison data:', err);
      setError('Failed to load comparison data. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  // Process the comparison data for the chart
  const processComparisonData = (responses: any[], selectedCompanyIds: number[]) => {
    // Create a map of years to data points
    const yearDataMap: Record<string, any> = {};
    
    // Process each company's metrics
    responses.forEach((response, index) => {
      if (!response || !response.data) return;
      
      const companyId = selectedCompanyIds[index];
      if (companyId === undefined) return;
      
      const company = companies.find(c => c.id === companyId);
      const companyName = company ? company.name : `Company ${companyId}`;
      
      // Process each metric
      if (typeof response.data !== 'object') return;
      
      Object.entries(response.data).forEach(([metricName, metricData]: [string, any]) => {
        if (!Array.isArray(metricData)) return;
        
        metricData.forEach((dataPoint: any) => {
          if (!dataPoint || typeof dataPoint !== 'object') return;
          
          const year = dataPoint.year;
          if (!year) return;
          
          if (!yearDataMap[year]) {
            yearDataMap[year] = { year };
          }
          
          // Add the metric value with company name as key
          const value = parseFloat(dataPoint.value);
          if (!isNaN(value)) {
            yearDataMap[year][`${metricName}_${companyId}`] = value;
            yearDataMap[year][`${metricName}_${companyId}_name`] = companyName;
          }
        });
      });
    });
    
    // Convert the map to an array and sort by year
    return Object.values(yearDataMap).sort((a, b) => {
      if (!a.year || !b.year) return 0;
      return String(a.year).localeCompare(String(b.year));
    });
  };

  // Get chart data keys for selected metrics and companies
  const getChartDataKeys = () => {
    const keys: string[] = [];
    
    selectedMetrics.forEach(metric => {
      selectedCompanies.forEach(companyId => {
        keys.push(`${metric}_${companyId}`);
      });
    });
    
    return keys;
  };

  // Get chart colors
  const getChartColors = () => {
    const baseColors = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe', '#00C49F', '#FFBB28', '#FF8042'];
    const colors: string[] = [];
    
    // Generate enough colors for all data series
    const totalSeries = selectedMetrics.length * selectedCompanies.length;
    for (let i = 0; i < totalSeries; i++) {
      colors.push(baseColors[i % baseColors.length]);
    }
    
    return colors;
  };

  // Format the name for the legend
  const formatLegendName = (dataKey: string) => {
    const [metric, companyId] = dataKey.split('_');
    const company = companies.find(c => c.id === parseInt(companyId));
    return `${company?.name || `Company ${companyId}`} - ${metric}`;
  };

  return (
    <PageLayout>
      <Typography variant="h4" component="h1" gutterBottom>
        Compare Reports
      </Typography>
      
      <Paper sx={{ p: 4, mb: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel id="company-select-label">Select Company</InputLabel>
              <Select
                labelId="company-select-label"
                id="company-select"
                value=""
                label="Select Company"
                onChange={handleCompanyChange as any}
              >
                {companies.map((company) => (
                  <MenuItem 
                    key={company.id} 
                    value={company.id}
                    disabled={selectedCompanies.includes(company.id)}
                  >
                    {company.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {selectedCompanies.map(companyId => {
                const company = companies.find(c => c.id === companyId);
                return (
                  <Chip 
                    key={companyId}
                    label={company ? company.name : `Company ${companyId}`}
                    onDelete={() => handleRemoveCompany(companyId)}
                    color="primary"
                    variant="outlined"
                  />
                );
              })}
            </Box>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              Select Metrics to Compare
            </Typography>
            <FormGroup row>
              {availableMetrics.map(metric => (
                <FormControlLabel
                  key={metric}
                  control={
                    <Checkbox
                      checked={selectedMetrics.includes(metric)}
                      onChange={handleMetricChange}
                      name={metric}
                    />
                  }
                  label={metric.charAt(0).toUpperCase() + metric.slice(1).replace(/([A-Z])/g, ' $1')}
                />
              ))}
            </FormGroup>
          </Grid>
          
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
              <Button
                variant="contained"
                onClick={handleCompare}
                disabled={selectedCompanies.length === 0 || selectedMetrics.length === 0 || loading}
              >
                {loading ? <CircularProgress size={24} /> : 'Compare'}
              </Button>
              
              <Button
                variant="outlined"
                onClick={handleChartTypeChange}
                disabled={comparisonData.length === 0}
              >
                Switch to {chartType === 'line' ? 'Bar' : 'Line'} Chart
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}
      
      {comparisonData.length > 0 ? (
        <FinancialPerformanceChart
          title="Financial Metrics Comparison"
          data={comparisonData}
          dataKeys={getChartDataKeys()}
          xAxisKey="year"
          colors={getChartColors()}
          chartType={chartType}
        />
      ) : !loading && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6">
            Select companies and metrics to compare
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            This page allows you to compare financial metrics across different companies and time periods.
          </Typography>
        </Paper>
      )}
    </PageLayout>
  );
} 