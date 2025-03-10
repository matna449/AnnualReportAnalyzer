'use client';

import React, { useEffect, useState } from 'react';
import { 
  Typography, 
  Box, 
  Grid, 
  Paper,
  CircularProgress,
  Alert,
  Button,
  Tabs,
  Tab
} from '@mui/material';
import {
  BarChart as BarChartIcon,
  Business as BusinessIcon,
  Description as DescriptionIcon,
  TrendingUp as TrendingUpIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import PageLayout from '@/components/PageLayout';
import SummaryCard from '@/components/SummaryCard';
import FinancialPerformanceChart from '@/components/FinancialPerformanceChart';
import CompanyList from '@/components/CompanyList';

// Define interface for metrics data structure
interface CompanyMetricsData {
  metrics: Record<string, Array<{
    id: number;
    year: number | string;
    value: number | string;
    unit: string;
  }>>;
}

// Dashboard page component
export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [recentReports, setRecentReports] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<number | null>(null);
  const [companyMetrics, setCompanyMetrics] = useState<CompanyMetricsData | null>(null);
  const [selectedMetricType, setSelectedMetricType] = useState('revenue');
  const [tabValue, setTabValue] = useState<string>('executive');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch dashboard summary data
        const summaryResponse = await fetch('/api/dashboard/summary');
        if (!summaryResponse.ok) {
          const summaryErrorText = await summaryResponse.text();
          console.error('Dashboard summary error details:', summaryErrorText);
          throw new Error(`Failed to fetch dashboard summary: ${summaryResponse.status} ${summaryResponse.statusText}`);
        }
        const summaryData = await summaryResponse.json();
        
        // Fetch recent reports
        const reportsResponse = await fetch('/api/dashboard/recent-reports');
        if (!reportsResponse.ok) {
          const reportsErrorText = await reportsResponse.text();
          console.error('Recent reports error details:', reportsErrorText);
          throw new Error(`Failed to fetch recent reports: ${reportsResponse.status} ${reportsResponse.statusText}`);
        }
        const reportsData = await reportsResponse.json();
        
        // Fetch companies
        const companiesResponse = await fetch('/api/companies/');
        if (!companiesResponse.ok) {
          const companiesErrorText = await companiesResponse.text();
          console.error('Companies error details:', companiesErrorText);
          throw new Error(`Failed to fetch companies: ${companiesResponse.status} ${companiesResponse.statusText}`);
        }
        const companiesData = await companiesResponse.json();
        
        setDashboardData(summaryData);
        setRecentReports(reportsData);
        setCompanies(companiesData);
        
        // Set the first company as selected if available
        if (companiesData.length > 0) {
          setSelectedCompany(companiesData[0].id);
        }
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError(err instanceof Error ? err.message : 'An error occurred while fetching dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  useEffect(() => {
    const fetchCompanyMetrics = async () => {
      if (!selectedCompany) return;
      
      try {
        // Fetch metrics for the selected company
        const metricsResponse = await fetch(`/api/companies/${selectedCompany}/metrics?metric_names=Revenue&metric_names=Net%20Income&metric_names=EPS&metric_names=EBITDA&metric_names=Profit%20Margin`);
        if (!metricsResponse.ok) {
          console.error('Failed to fetch company metrics');
          return;
        }
        
        const metricsData = await metricsResponse.json();
        setCompanyMetrics(metricsData);
      } catch (err) {
        console.error('Error fetching company metrics:', err);
      }
    };

    fetchCompanyMetrics();
  }, [selectedCompany]);

  // Format data for the chart
  const getChartData = () => {
    if (!dashboardData || !dashboardData.year_counts) {
      return [];
    }
    
    return Object.entries(dashboardData.year_counts)
      .map(([year, count]) => ({
        year,
        reports: count as number
      }))
      .sort((a, b) => parseInt(a.year) - parseInt(b.year));
  };

  // Format companies data for the list
  const getCompaniesData = () => {
    if (!recentReports) {
      return [];
    }
    
    return recentReports.map(report => ({
      id: report.id,
      name: report.company_name,
      ticker: 'N/A', // This would come from your actual data
      sector: 'N/A', // This would come from your actual data
      latestReport: report.year,
      status: report.processing_status
    }));
  };

  // Get financial metrics data for the selected company
  const getFinancialMetricsData = () => {
    if (!companyMetrics || !companyMetrics.metrics) {
      return [];
    }
    
    // The metrics structure is now different
    const metricsByYear: Record<string, any> = {};
    const metrics = companyMetrics.metrics;
    
    // Process each metric type (Revenue, Net Income, etc.)
    Object.entries(metrics).forEach(([metricName, values]) => {
      if (!Array.isArray(values)) return;
      
      // Each value has year and value properties
      values.forEach(item => {
        if (!item || typeof item !== 'object' || !item.year) return;
        
        const year = item.year.toString();
        
        if (!metricsByYear[year]) {
          metricsByYear[year] = { year };
        }
        
        // Clean up the value (remove currency symbols, convert to number)
        let value = item.value;
        if (typeof value === 'string') {
          value = value.replace(/[$,]/g, '');
          value = parseFloat(value);
          if (isNaN(value)) return; // Skip if not a valid number
        } else if (typeof value !== 'number') {
          return; // Skip if not a string or number
        }
        
        // Normalize the metric name to camelCase for the chart
        const metricKey = metricName
          .toLowerCase()
          .replace(/[^a-z0-9]+(.)/g, (_: string, char: string) => char.toUpperCase());
        
        metricsByYear[year][metricKey] = value;
      });
    });
    
    return Object.values(metricsByYear).sort((a, b) => parseInt(a.year) - parseInt(b.year));
  };

  const handleCompanyChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedCompany(newValue);
  };

  const handleMetricTypeChange = (event: React.SyntheticEvent, newValue: string) => {
    setSelectedMetricType(newValue);
  };

  if (loading) {
    return (
      <PageLayout>
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout>
        <Alert severity="error" sx={{ my: 2 }}>
          {error}
        </Alert>
        <Button 
          variant="contained" 
          startIcon={<RefreshIcon />} 
          onClick={() => window.location.reload()}
        >
          Retry
        </Button>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Overview of your annual report analysis
        </Typography>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard 
            title="Companies" 
            value={dashboardData?.company_count || 0}
            icon={<BusinessIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard 
            title="Reports" 
            value={dashboardData?.report_count || 0}
            icon={<DescriptionIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard 
            title="Completed" 
            value={dashboardData?.status_counts?.completed || 0}
            icon={<TrendingUpIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard 
            title="Processing" 
            value={dashboardData?.status_counts?.processing || 0}
            icon={<BarChartIcon />}
          />
        </Grid>
      </Grid>

      {/* Charts and Tables */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Reports by Year
            </Typography>
            <FinancialPerformanceChart 
              title="" 
              data={getChartData()}
              dataKeys={['reports']}
              xAxisKey="year"
              colors={['#8884d8']}
            />
          </Paper>
          
          {/* Latest Summaries Section */}
          {dashboardData?.latest_summaries && Object.keys(dashboardData.latest_summaries).length > 0 && (
            <Paper sx={{ p: 2, mb: 3 }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <DescriptionIcon sx={{ mr: 1, color: 'primary.main' }} />
                Latest Report Insights
              </Typography>
              
              <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                <Tabs 
                  value={tabValue || 'executive'} 
                  onChange={(e, newValue) => setTabValue(newValue)}
                  variant="scrollable"
                  scrollButtons="auto"
                  textColor="primary"
                  indicatorColor="primary"
                >
                  {dashboardData.latest_summaries.executive && (
                    <Tab label="Executive Summary" value="executive" />
                  )}
                  {dashboardData.latest_summaries.risks && (
                    <Tab label="Risk Factors" value="risks" />
                  )}
                  {dashboardData.latest_summaries.outlook && (
                    <Tab label="Business Outlook" value="outlook" />
                  )}
                  {dashboardData.latest_summaries.sentiment && (
                    <Tab label="Sentiment" value="sentiment" />
                  )}
                </Tabs>
              </Box>
              
              <Box sx={{ p: 2, minHeight: '200px', maxHeight: '300px', overflowY: 'auto' }}>
                {tabValue === 'executive' && dashboardData.latest_summaries.executive && (
                  <Paper elevation={0} sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2 }}>
                    <Typography variant="body1" sx={{ lineHeight: 1.7, textAlign: 'justify' }}>
                      {dashboardData.latest_summaries.executive}
                    </Typography>
                  </Paper>
                )}
                {tabValue === 'risks' && dashboardData.latest_summaries.risks && (
                  <Paper 
                    elevation={0} 
                    sx={{ 
                      p: 2, 
                      bgcolor: 'info.light', 
                      color: 'info.dark',
                      borderRadius: 2 
                    }}
                  >
                    <Typography variant="body1" sx={{ lineHeight: 1.7, textAlign: 'justify' }}>
                      {dashboardData.latest_summaries.risks}
                    </Typography>
                  </Paper>
                )}
                {tabValue === 'outlook' && dashboardData.latest_summaries.outlook && (
                  <Paper 
                    elevation={0} 
                    sx={{ 
                      p: 2, 
                      bgcolor: 'info.light', 
                      color: 'info.dark',
                      borderRadius: 2 
                    }}
                  >
                    <Typography variant="body1" sx={{ lineHeight: 1.7, textAlign: 'justify' }}>
                      {dashboardData.latest_summaries.outlook}
                    </Typography>
                  </Paper>
                )}
                {tabValue === 'sentiment' && dashboardData.latest_summaries.sentiment && (
                  <Paper 
                    elevation={0} 
                    sx={{ 
                      p: 2, 
                      bgcolor: dashboardData.latest_summaries.sentiment.includes('positive') ? 'success.light' : 
                              dashboardData.latest_summaries.sentiment.includes('negative') ? 'error.light' : 'info.light',
                      color: dashboardData.latest_summaries.sentiment.includes('positive') ? 'success.dark' : 
                             dashboardData.latest_summaries.sentiment.includes('negative') ? 'error.dark' : 'info.dark',
                      borderRadius: 2
                    }}
                  >
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      {dashboardData.latest_summaries.sentiment.includes('positive') ? '😀 Positive' : 
                       dashboardData.latest_summaries.sentiment.includes('negative') ? '😟 Negative' : '😐 Neutral'}
                    </Typography>
                    <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                      {dashboardData.latest_summaries.sentiment}
                    </Typography>
                  </Paper>
                )}
              </Box>
            </Paper>
          )}
          
          {companies.length > 0 && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Financial Metrics Comparison
              </Typography>
              
              <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                <Tabs 
                  value={selectedCompany} 
                  onChange={handleCompanyChange}
                  variant="scrollable"
                  scrollButtons="auto"
                >
                  {companies.map(company => (
                    <Tab 
                      key={company.id} 
                      label={company.name} 
                      value={company.id} 
                    />
                  ))}
                </Tabs>
              </Box>
              
              <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                <Tabs 
                  value={selectedMetricType} 
                  onChange={handleMetricTypeChange}
                >
                  <Tab label="Revenue" value="revenue" />
                  <Tab label="Net Income" value="netIncome" />
                  <Tab label="Profit Margin" value="profitMargin" />
                </Tabs>
              </Box>
              
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  {companies.find(c => c.id === selectedCompany)?.name || 'Company'} Financial Performance
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {selectedMetricType === 'revenue' && 'Annual revenue figures in USD'}
                  {selectedMetricType === 'netIncome' && 'Annual net income in USD'}
                  {selectedMetricType === 'eps' && 'Earnings per share in USD'}
                  {selectedMetricType === 'ebitda' && 'EBITDA in USD'}
                  {selectedMetricType === 'profitMargin' && 'Profit margin as percentage'}
                </Typography>
              </Box>
              
              {companyMetrics && companyMetrics.metrics && Object.keys(companyMetrics.metrics).length > 0 ? (
                <FinancialPerformanceChart 
                  title="" 
                  data={getFinancialMetricsData()}
                  dataKeys={[selectedMetricType]}
                  xAxisKey="year"
                  colors={['#82ca9d']}
                />
              ) : (
                <Alert severity="info">No financial metrics available for this company.</Alert>
              )}
            </Paper>
          )}
        </Grid>
        
        <Grid item xs={12} md={6}>
          <CompanyList 
            title="Recent Reports" 
            companies={getCompaniesData()}
          />
        </Grid>

        {/* Financial Performance Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Financial Performance
            </Typography>
            
            {selectedCompany ? (
              <>
                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                  <Tabs 
                    value={selectedMetricType} 
                    onChange={handleMetricTypeChange}
                  >
                    <Tab label="Revenue" value="revenue" />
                  </Tabs>
                </Box>
              </>
            ) : (
              <Alert severity="info">Select a company to view financial performance</Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </PageLayout>
  );
} 