'use client';

import React, { useEffect, useState } from 'react';
import { 
  Typography, 
  Box, 
  Grid, 
  Paper,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  BarChart as BarChartIcon,
  Business as BusinessIcon,
  Description as DescriptionIcon,
  TrendingUp as TrendingUpIcon
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

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
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
        
        setDashboardData(summaryData);
        setRecentReports(reportsData);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError(err instanceof Error ? err.message : 'An error occurred while fetching dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

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
      latestReport: report.year.toString(),
      status: report.processing_status
    }));
  };

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

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error" sx={{ my: 2 }}>
          {error}
        </Alert>
      ) : (
        <>
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
                value={dashboardData?.status_counts?.Completed || 0}
                icon={<TrendingUpIcon />}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <SummaryCard 
                title="Processing" 
                value={dashboardData?.status_counts?.Processing || 0}
                icon={<BarChartIcon />}
              />
            </Grid>
          </Grid>

          {/* Charts and Tables */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FinancialPerformanceChart 
                title="Reports by Year" 
                data={getChartData()}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <CompanyList 
                title="Recent Reports" 
                companies={getCompaniesData()}
              />
            </Grid>
          </Grid>
        </>
      )}
    </PageLayout>
  );
} 