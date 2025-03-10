'use client';

import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Box, 
  Paper,
  Grid,
  Tabs,
  Tab,
  Divider,
  Chip,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Button,
  CircularProgress,
  Alert
} from '@mui/material';
import { 
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Analytics as AnalyticsIcon,
  SentimentSatisfiedAlt as SentimentSatisfiedAltIcon,
  SentimentDissatisfied as SentimentDissatisfiedIcon,
  SentimentNeutral as SentimentNeutralIcon,
  WarningAmber as WarningAmberIcon,
  Business as BusinessIcon,
  AttachMoney as AttachMoneyIcon
} from '@mui/icons-material';
import PageLayout from '@/components/PageLayout';
import LogViewer from '@/components/LogViewer';
import { shouldShowLogs } from '@/utils/featureFlags';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`report-tabpanel-${index}`}
      aria-labelledby={`report-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export default function ReportDetails({ params }: { params: { id: string } }) {
  // Convert string ID from URL to number for consistency with backend
  const reportId = parseInt(params.id, 10);
  
  // Validate that reportId is a valid number
  const isValidId = !isNaN(reportId) && reportId > 0;
  
  const [reportData, setReportData] = useState<any>(null);
  const [relatedReports, setRelatedReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [showLogs, setShowLogs] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    // Don't fetch if ID is invalid
    if (!isValidId) {
      setError("Invalid report ID. Please check the URL and try again.");
      setLoading(false);
      return;
    }
    
    fetchReportData();
  }, [reportId, isValidId]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const fetchReportData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log(`Fetching report data for ID: ${reportId}`);
      const response = await fetch(`/api/reports/${reportId}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`API error (${response.status}): ${errorText}`);
        throw new Error(`Failed to fetch report: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Report data received:', data);
      
      setReportData(data);
      
      // Set tab value based on data availability
      if (data.summaries && Object.keys(data.summaries).length > 0) {
        setTabValue(0); // Overview tab
      } else if (data.metrics && data.metrics.length > 0) {
        setTabValue(1); // Metrics tab
      }
      
      // Fetch related reports if company_id is available
      if (data.company_id) {
        const relatedResponse = await fetch(`/api/companies/${data.company_id}/reports`);
        if (relatedResponse.ok) {
          const relatedData = await relatedResponse.json();
          // Filter out the current report
          setRelatedReports(relatedData.filter((report: any) => report.id !== data.id));
        }
      }
    } catch (err) {
      console.error("Error fetching report data:", err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!reportData) return;
    
    // Create CSV content
    let csvContent = "data:text/csv;charset=utf-8,";
    
    // Add report info
    csvContent += `Report ID,${reportData.id}\n`;
    csvContent += `Company,${reportData.company_name}\n`;
    csvContent += `Year,${reportData.year}\n`;
    csvContent += `Upload Date,${reportData.upload_date}\n\n`;
    
    // Add metrics - safely handle if metrics is undefined
    csvContent += "Metric Name,Value,Unit\n";
    if (reportData.metrics && Array.isArray(reportData.metrics)) {
      reportData.metrics.forEach((metric: any) => {
        csvContent += `${metric.name},${metric.value},${metric.unit}\n`;
      });
    } else {
      csvContent += "No metrics available,,\n";
    }
    
    // Add summaries - safely handle if summaries is undefined
    csvContent += "\nSummaries\n";
    if (reportData.summaries && typeof reportData.summaries === 'object') {
      Object.entries(reportData.summaries).forEach(([key, value]: [string, any]) => {
        if (value) {
          csvContent += `${key},${value.replace(/,/g, ';').replace(/\n/g, ' ')}\n`;
        }
      });
    } else {
      csvContent += "No summaries available,\n";
    }
    
    // Create download link
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `report_${reportData.company_name}_${reportData.year}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!mounted) {
    return null;
  }

  if (loading) {
    return (
      <PageLayout>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
          <CircularProgress />
        </Box>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout>
        <Alert severity="error" sx={{ mb: 2 }}>
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

  if (!reportData) {
    return (
      <PageLayout>
        <Alert severity="info">No report data found.</Alert>
      </PageLayout>
    );
  }

  // Format metrics for display - safely handle if metrics is undefined
  const financialMetrics = reportData.metrics && Array.isArray(reportData.metrics) 
    ? reportData.metrics.filter((m: any) => 
        ['revenue', 'income', 'profit', 'eps', 'ebitda', 'assets', 'liabilities', 'equity', 'cash'].some(
          term => m.name.toLowerCase().includes(term)
        )
      )
    : [];

  const keyMetrics = reportData.metrics && Array.isArray(reportData.metrics)
    ? reportData.metrics.filter((m: any) => 
        ['margin', 'growth', 'ratio', 'return', 'roi', 'roe', 'roa'].some(
          term => m.name.toLowerCase().includes(term)
        )
      )
    : [];

  return (
    <PageLayout>
      <Box sx={{ py: 4 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ mb: 4 }}>
            {error}
          </Alert>
        ) : reportData ? (
          <>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
              <Box>
                <Typography variant="h4" component="h1" gutterBottom>
                  {reportData.company_name} Annual Report
                </Typography>
                <Typography variant="subtitle1" color="text.secondary">
                  {reportData.year} • {new Date(reportData.upload_date).toLocaleDateString()}
                </Typography>
              </Box>
              
              <Box>
                <Button 
                  variant="outlined" 
                  startIcon={<DownloadIcon />}
                  href={`/api/reports/${reportId}/download`}
                  sx={{ mr: 2 }}
                >
                  Download PDF
                </Button>
                
                <Button 
                  variant="outlined" 
                  startIcon={<RefreshIcon />}
                  onClick={() => window.location.reload()}
                >
                  Refresh
                </Button>
              </Box>
            </Box>
            
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs 
                value={tabValue} 
                onChange={handleTabChange} 
                aria-label="report tabs"
                variant="scrollable"
                scrollButtons="auto"
              >
                <Tab label="Overview" id="report-tab-0" aria-controls="report-tabpanel-0" />
                <Tab label="Metrics" id="report-tab-1" aria-controls="report-tabpanel-1" />
                <Tab label="Insights" id="report-tab-2" aria-controls="report-tabpanel-2" />
                <Tab label="Financial Data" id="report-tab-3" aria-controls="report-tabpanel-3" />
                <Tab label="Raw Text" id="report-tab-4" aria-controls="report-tabpanel-4" />
                {shouldShowLogs() && (
                  <Tab label="Logs" id="report-tab-5" aria-controls="report-tabpanel-5" onClick={() => setShowLogs(true)} />
                )}
              </Tabs>
            </Box>
            
            <TabPanel value={tabValue} index={0}>
              <Paper elevation={0} sx={{ p: 3, mb: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
                <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium' }}>
                  Executive Summary
                </Typography>
                <Typography variant="body1" paragraph sx={{ lineHeight: 1.7, textAlign: 'justify' }}>
                  {reportData.summaries?.executive || "No executive summary available."}
                </Typography>
              </Paper>
              
              <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
                <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium' }}>
                  Sentiment Analysis
                </Typography>
                
                {reportData.summaries?.sentiment ? (
                  <>
                    <Box sx={{ 
                      mb: 3, 
                      p: 2, 
                      borderRadius: 1, 
                      bgcolor: reportData.summaries.sentiment.includes('positive') ? 'success.light' : 
                              reportData.summaries.sentiment.includes('negative') ? 'error.light' : 'info.light'
                    }}>
                      <Typography variant="h6" sx={{ 
                        color: reportData.summaries.sentiment.includes('positive') ? 'success.dark' : 
                              reportData.summaries.sentiment.includes('negative') ? 'error.dark' : 'info.dark',
                        display: 'flex',
                        alignItems: 'center'
                      }}>
                        {reportData.summaries.sentiment.includes('positive') ? '😀 Positive' : 
                         reportData.summaries.sentiment.includes('negative') ? '😟 Negative' : '😐 Neutral'}
                      </Typography>
                    </Box>
                    <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                      {reportData.summaries.sentiment}
                    </Typography>
                  </>
                ) : (
                  <Alert severity="info">No sentiment analysis available.</Alert>
                )}
              </Paper>
            </TabPanel>
            
            <TabPanel value={tabValue} index={1}>
              {financialMetrics.length > 0 ? (
                <Grid container spacing={3}>
                  {financialMetrics.map((metric: any, index: number) => (
                    <Grid item xs={12} sm={6} md={4} key={index}>
                      <Card sx={{ 
                        transition: 'transform 0.2s, box-shadow 0.2s', 
                        '&:hover': { 
                          transform: 'translateY(-4px)', 
                          boxShadow: 4 
                        } 
                      }}>
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            {metric.name}
                          </Typography>
                          <Typography variant="h5" component="div" color="primary.main" sx={{ fontWeight: 'bold' }}>
                            {metric.value} {metric.unit}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              ) : (
                <Alert severity="info">No financial metrics available.</Alert>
              )}
            </TabPanel>
            
            <TabPanel value={tabValue} index={2}>
              <Paper elevation={0} sx={{ p: 3, mb: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
                <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium' }}>
                  Risk Factors
                </Typography>
                {reportData.summaries?.risks ? (
                  <Box component="div" sx={{ maxHeight: '400px', overflowY: 'auto', pr: 2 }}>
                    {reportData.summaries.risks.split('\n').map((risk: string, index: number) => (
                      <Paper 
                        key={index} 
                        elevation={0}
                        sx={{ 
                          p: 2, 
                          mb: 2, 
                          bgcolor: 'error.light', 
                          color: 'error.dark',
                          borderRadius: 1
                        }}
                      >
                        <Typography variant="body1">
                          {risk}
                        </Typography>
                      </Paper>
                    ))}
                  </Box>
                ) : (
                  <Alert severity="info">No risk factors available.</Alert>
                )}
              </Paper>
              
              <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
                <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium' }}>
                  Business Outlook
                </Typography>
                {reportData.summaries?.outlook ? (
                  <Box sx={{ 
                    p: 2, 
                    borderRadius: 1, 
                    bgcolor: 'info.light', 
                    color: 'info.dark' 
                  }}>
                    <Typography variant="body1" sx={{ lineHeight: 1.7, textAlign: 'justify' }}>
                      {reportData.summaries.outlook}
                    </Typography>
                  </Box>
                ) : (
                  <Alert severity="info">No business outlook available.</Alert>
                )}
              </Paper>
            </TabPanel>
            
            <TabPanel value={tabValue} index={3}>
              {/* Financial Data Tab Content */}
            </TabPanel>
            
            <TabPanel value={tabValue} index={4}>
              {/* Raw Text Tab Content */}
            </TabPanel>
            
            {shouldShowLogs() && (
              <TabPanel value={tabValue} index={5}>
                {showLogs && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      Processing Logs
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      These logs show the processing steps for this report. They can help diagnose issues if the analysis is incomplete.
                    </Typography>
                    <LogViewer 
                      reportId={reportId} 
                      height={500} 
                      label={`Report ${reportId} Processing Logs`} 
                    />
                  </Box>
                )}
              </TabPanel>
            )}
          </>
        ) : (
          <Alert severity="info">No report data found.</Alert>
        )}
      </Box>
    </PageLayout>
  );
}