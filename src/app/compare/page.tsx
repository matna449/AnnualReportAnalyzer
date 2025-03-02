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
  Checkbox,
  Tabs,
  Tab
} from '@mui/material';
import PageLayout from '@/components/PageLayout';
import FinancialPerformanceChart from '@/components/FinancialPerformanceChart';
import axios from 'axios';

export default function ComparePage() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [selectedCompanies, setSelectedCompanies] = useState<number[]>([]);
  const [selectedReports, setSelectedReports] = useState<number[]>([]);
  const [availableMetrics, setAvailableMetrics] = useState<string[]>([
    'revenue', 'netIncome', 'operatingIncome', 'grossMargin', 'operatingMargin', 'netMargin',
    'eps', 'totalAssets', 'totalLiabilities', 'cashFlow', 'rnd'
  ]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['revenue']);
  const [comparisonData, setComparisonData] = useState<any[]>([]);
  const [summaryComparison, setSummaryComparison] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');
  const [activeTab, setActiveTab] = useState<string>('metrics');
  const [comparisonMode, setComparisonMode] = useState<'companies' | 'reports'>('companies');

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

    const fetchReports = async () => {
      try {
        const response = await axios.get('/api/reports/');
        setReports(response.data);
      } catch (err) {
        console.error('Error fetching reports:', err);
        setError('Failed to load reports. Please try again later.');
      }
    };

    fetchCompanies();
    fetchReports();
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
    if (comparisonMode === 'companies') {
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
        setSummaryComparison(null); // Reset summary comparison
      } catch (err) {
        console.error('Error fetching comparison data:', err);
        setError('Failed to load comparison data. Please try again later.');
      } finally {
        setLoading(false);
      }
    } else {
      // Report comparison mode
      if (selectedReports.length < 2) {
        setError('Please select at least two reports to compare');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Use the enhanced compare reports endpoint
        const response = await axios.post('/api/reports/compare', {
          report_ids: selectedReports,
          metrics: selectedMetrics
        });
        
        // Process metrics data for charts
        const metricsData = [];
        const metricsComparison = response.data.metrics_comparison || {};
        
        for (const metricName in metricsComparison) {
          const metricData = metricsComparison[metricName];
          for (const reportId in metricData) {
            const reportInfo = metricData[reportId];
            metricsData.push({
              year: reportInfo.year,
              company: reportInfo.company_name,
              metric: metricName,
              value: parseFloat(reportInfo.value.replace(/[^0-9.-]+/g, '')),
              reportId: parseInt(reportId)
            });
          }
        }
        
        setComparisonData(metricsData);
        
        // Set summary comparison data
        setSummaryComparison({
          reports: response.data.reports,
          summaries: response.data.summaries_comparison,
          aiAnalysis: response.data.ai_analysis
        });
        
        // Switch to summaries tab if available
        if (response.data.ai_analysis && Object.keys(response.data.ai_analysis).length > 0) {
          setActiveTab('summaries');
        }
      } catch (err) {
        console.error('Error comparing reports:', err);
        setError('Failed to compare reports. Please try again later.');
      } finally {
        setLoading(false);
      }
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
      
      <Paper sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>Comparison Mode</InputLabel>
              <Select
                value={comparisonMode}
                onChange={(e) => {
                  setComparisonMode(e.target.value as 'companies' | 'reports');
                  setSelectedCompanies([]);
                  setSelectedReports([]);
                  setComparisonData([]);
                  setSummaryComparison(null);
                }}
                label="Comparison Mode"
              >
                <MenuItem value="companies">Compare Companies</MenuItem>
                <MenuItem value="reports">Compare Reports</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          {comparisonMode === 'companies' ? (
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Select Companies</InputLabel>
                <Select
                  multiple
                  value={selectedCompanies}
                  onChange={(e) => setSelectedCompanies(e.target.value as number[])}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(selected as number[]).map((companyId) => {
                        const company = companies.find(c => c.id === companyId);
                        return (
                          <Chip 
                            key={companyId} 
                            label={company ? company.name : companyId} 
                            onDelete={() => handleRemoveCompany(companyId)}
                            onMouseDown={(event) => event.stopPropagation()}
                          />
                        );
                      })}
                    </Box>
                  )}
                >
                  {companies.map((company) => (
                    <MenuItem key={company.id} value={company.id}>
                      {company.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          ) : (
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Select Reports</InputLabel>
                <Select
                  multiple
                  value={selectedReports}
                  onChange={(e) => setSelectedReports(e.target.value as number[])}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(selected as number[]).map((reportId) => {
                        const report = reports.find(r => r.id === reportId);
                        return (
                          <Chip 
                            key={reportId} 
                            label={report ? `${report.company_name} (${report.year})` : reportId} 
                            onDelete={() => setSelectedReports(selectedReports.filter(id => id !== reportId))}
                            onMouseDown={(event) => event.stopPropagation()}
                          />
                        );
                      })}
                    </Box>
                  )}
                >
                  {reports.map((report) => (
                    <MenuItem key={report.id} value={report.id}>
                      {report.company_name} ({report.year})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          )}
          
          <Grid item xs={12}>
            <Typography variant="subtitle1" gutterBottom>
              Select Metrics to Compare
            </Typography>
            <FormGroup row>
              {availableMetrics.map((metric) => (
                <FormControlLabel
                  key={metric}
                  control={
                    <Checkbox
                      checked={selectedMetrics.includes(metric)}
                      onChange={handleMetricChange}
                      name={metric}
                    />
                  }
                  label={formatLegendName(metric)}
                />
              ))}
            </FormGroup>
          </Grid>
          
          <Grid item xs={12}>
            <Button 
              variant="contained" 
              color="primary" 
              onClick={handleCompare}
              disabled={loading}
              sx={{ mr: 2 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Compare'}
            </Button>
            
            <Button 
              variant="outlined"
              onClick={handleChartTypeChange}
              disabled={loading || comparisonData.length === 0}
            >
              Switch to {chartType === 'line' ? 'Bar' : 'Line'} Chart
            </Button>
          </Grid>
        </Grid>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {comparisonData.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Tabs 
              value={activeTab} 
              onChange={(e, newValue) => setActiveTab(newValue)}
              textColor="primary"
              indicatorColor="primary"
            >
              <Tab label="Metrics Comparison" value="metrics" />
              {summaryComparison && <Tab label="Summary Comparison" value="summaries" />}
            </Tabs>
          </Box>
          
          {activeTab === 'metrics' && (
            <>
              <Typography variant="h6" gutterBottom>
                Metrics Comparison
              </Typography>
              <Box sx={{ height: 400, width: '100%' }}>
                <FinancialPerformanceChart
                  title=""
                  data={comparisonData}
                  dataKeys={getChartDataKeys()}
                  xAxisKey="year"
                  colors={getChartColors()}
                  chartType={chartType}
                />
              </Box>
            </>
          )}
          
          {activeTab === 'summaries' && summaryComparison && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Summary Comparison
                </Typography>
              </Grid>
              
              {/* AI Analysis Section */}
              {summaryComparison.aiAnalysis && Object.keys(summaryComparison.aiAnalysis).length > 0 && (
                <Grid item xs={12}>
                  <Paper elevation={0} sx={{ p: 3, mb: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
                    <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium' }}>
                      AI Comparison Analysis
                    </Typography>
                    
                    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                      <Tabs 
                        value={Object.keys(summaryComparison.aiAnalysis)[0]} 
                        onChange={(e, newValue) => setActiveTab(newValue)}
                        variant="scrollable"
                        scrollButtons="auto"
                      >
                        {Object.keys(summaryComparison.aiAnalysis).map(category => (
                          <Tab 
                            key={category} 
                            label={formatLegendName(category)} 
                            value={category} 
                          />
                        ))}
                      </Tabs>
                    </Box>
                    
                    {Object.entries(summaryComparison.aiAnalysis).map(([category, analysis]) => (
                      <Box 
                        key={category} 
                        sx={{ 
                          display: activeTab === category ? 'block' : 'none',
                          whiteSpace: 'pre-line'
                        }}
                      >
                        <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                          {analysis as string}
                        </Typography>
                      </Box>
                    ))}
                  </Paper>
                </Grid>
              )}
              
              {/* Side by Side Comparison */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Side by Side Comparison
                </Typography>
                
                <Grid container spacing={2}>
                  {summaryComparison.reports.map((report: any, index: number) => {
                    const reportSummaries = summaryComparison.summaries[report.id]?.summaries || {};
                    return (
                      <Grid item xs={12} md={6} key={report.id}>
                        <Paper 
                          elevation={3} 
                          sx={{ 
                            p: 2, 
                            height: '100%',
                            bgcolor: index === 0 ? 'primary.light' : 'secondary.light',
                            color: index === 0 ? 'primary.contrastText' : 'secondary.contrastText'
                          }}
                        >
                          <Typography variant="h6" gutterBottom>
                            {report.company_name} ({report.year})
                          </Typography>
                          
                          {Object.entries(reportSummaries).map(([category, content]) => (
                            <Box key={category} sx={{ mb: 2 }}>
                              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                                {formatLegendName(category)}
                              </Typography>
                              <Typography variant="body2" sx={{ 
                                maxHeight: '150px', 
                                overflowY: 'auto',
                                whiteSpace: 'pre-line',
                                p: 1
                              }}>
                                {content as string}
                              </Typography>
                            </Box>
                          ))}
                        </Paper>
                      </Grid>
                    );
                  })}
                </Grid>
              </Grid>
            </Grid>
          )}
        </Paper>
      )}
    </PageLayout>
  );
} 