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

// Dashboard page component
export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [recentReports, setRecentReports] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<number | null>(null);
  const [companyMetrics, setCompanyMetrics] = useState<any[]>([]);
  const [metricType, setMetricType] = useState<string>('revenue');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch dashboard summary data
        const summaryResponse = await fetch('/api/dashboard/summary');
        if (!summaryResponse.ok) {
          throw new Error('Failed to fetch dashboard summary');
        }
        const summaryData = await summaryResponse.json();
        
        // Fetch recent reports
        const reportsResponse = await fetch('/api/dashboard/recent-reports');
        if (!reportsResponse.ok) {
          throw new Error('Failed to fetch recent reports');
        }
        const reportsData = await reportsResponse.json();
        
        // Fetch companies
        const companiesResponse = await fetch('/api/companies/');
        if (!companiesResponse.ok) {
          throw new Error('Failed to fetch companies');
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
    if (!companyMetrics || !Array.isArray(companyMetrics) || companyMetrics.length === 0) {
      return [];
    }
    
    // Transform the data for the chart
    const metricsByYear: Record<string, any> = {};
    
    companyMetrics.forEach(metric => {
      if (!metric || typeof metric !== 'object') return;
      
      const year = metric.year;
      if (!year) return;
      
      if (!metricsByYear[year]) {
        metricsByYear[year] = { year };
      }
      
      // Clean up the value (remove currency symbols, convert to number)
      let value = metric.value;
      if (typeof value === 'string') {
        value = value.replace(/[$,]/g, '');
        value = parseFloat(value);
        if (isNaN(value)) return; // Skip if not a valid number
      } else if (typeof value !== 'number') {
        return; // Skip if not a string or number
      }
      
      // Normalize the metric name to camelCase for the chart
      if (!metric.name || typeof metric.name !== 'string') return;
      
      const metricKey = metric.name
        .toLowerCase()
        .replace(/[^a-z0-9]+(.)/g, (_: string, char: string) => char.toUpperCase());
      
      metricsByYear[year][metricKey] = value;
    });
    
    return Object.values(metricsByYear).sort((a, b) => parseInt(a.year) - parseInt(b.year));
  };

  const handleCompanyChange = (event: React.SyntheticEvent, newValue: number) => {
    setSelectedCompany(newValue);
  };

  const handleMetricTypeChange = (event: React.SyntheticEvent, newValue: string) => {
    setMetricType(newValue);
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
                  value={metricType} 
                  onChange={handleMetricTypeChange}
                >
                  <Tab label="Revenue" value="revenue" />
                  <Tab label="Net Income" value="netIncome" />
                  <Tab label="Profit Margin" value="profitMargin" />
                </Tabs>
              </Box>
              
              {companyMetrics && Array.isArray(companyMetrics) && companyMetrics.length > 0 ? (
                <FinancialPerformanceChart 
                  title="" 
                  data={getFinancialMetricsData()}
                  dataKeys={[metricType]}
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
      </Grid>
    </PageLayout>
  );
} 