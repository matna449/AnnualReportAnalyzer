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
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<any>(null);
  const [relatedReports, setRelatedReports] = useState<any[]>([]);
  const [enhancedAnalysis, setEnhancedAnalysis] = useState<any>(null);
  const [loadingEnhanced, setLoadingEnhanced] = useState<boolean>(false);
  const [mounted, setMounted] = useState(false);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    
    // Load enhanced analysis when user clicks on the AI Analysis tab
    if (newValue === 3 && !enhancedAnalysis && reportData) {
      fetchEnhancedAnalysis();
    }
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const fetchReportData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch report data
        const response = await fetch(`/api/reports/${params.id}`);
        if (!response.ok) {
          throw new Error(`Error fetching report: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Fetch summaries
        const summariesResponse = await fetch(`/api/reports/${params.id}/summaries`);
        if (summariesResponse.ok) {
          const summariesData = await summariesResponse.json();
          data.summaries = summariesData;
        }
        
        setReportData(data);
        
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
        console.error('Error fetching report data:', err);
        setError(err instanceof Error ? err.message : 'An error occurred while fetching report data');
      } finally {
        setLoading(false);
      }
    };

    if (mounted) {
      fetchReportData();
    }
  }, [params.id, mounted]);

  const fetchEnhancedAnalysis = async () => {
    if (!reportData) return;
    
    setLoadingEnhanced(true);
    try {
      const response = await fetch(`/api/reports/${reportData.id}/enhanced-analysis`);
      if (!response.ok) {
        throw new Error(`Error fetching enhanced analysis: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      // If analysis is pending, trigger it and poll for results
      if (data.status === 'pending') {
        // Trigger analysis
        await fetch(`/api/reports/${reportData.id}/enhanced-analysis`, {
          method: 'POST'
        });
        
        // Poll for results every 5 seconds
        const pollInterval = setInterval(async () => {
          try {
            const pollResponse = await fetch(`/api/reports/${reportData.id}/enhanced-analysis`);
            if (pollResponse.ok) {
              const pollData = await pollResponse.json();
              if (pollData.status === 'success') {
                setEnhancedAnalysis(pollData.analysis);
                clearInterval(pollInterval);
                setLoadingEnhanced(false);
              }
            }
          } catch (err) {
            console.error('Error polling enhanced analysis:', err);
          }
        }, 5000);
        
        // Stop polling after 2 minutes (24 attempts)
        setTimeout(() => {
          clearInterval(pollInterval);
          if (loadingEnhanced) {
            setLoadingEnhanced(false);
            setError('Enhanced analysis is taking longer than expected. Please try again later.');
          }
        }, 120000);
      } else if (data.status === 'success') {
        setEnhancedAnalysis(data.analysis);
        setLoadingEnhanced(false);
      }
    } catch (err) {
      console.error('Error fetching enhanced analysis:', err);
      setError(err instanceof Error ? err.message : 'An error occurred while fetching enhanced analysis');
      setLoadingEnhanced(false);
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
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Typography variant="h4" component="h1" gutterBottom>
            {reportData.company_name}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Annual Report {reportData.year} • Uploaded on {new Date(reportData.upload_date).toLocaleDateString()}
          </Typography>
          <Box sx={{ mt: 1 }}>
            <Chip 
              label={reportData.processing_status} 
              color={reportData.processing_status === 'completed' ? 'success' : 'warning'} 
              size="small" 
            />
          </Box>
        </div>
        <Button 
          variant="outlined" 
          startIcon={<DownloadIcon />} 
          onClick={handleExportCSV}
        >
          Export CSV
        </Button>
      </Box>
      
      <Grid container spacing={3}>
        {/* Main Content */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ width: '100%' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs 
                value={tabValue} 
                onChange={handleTabChange} 
                aria-label="report tabs"
              >
                <Tab label="Summary" id="report-tab-0" aria-controls="report-tabpanel-0" />
                <Tab label="Financials" id="report-tab-1" aria-controls="report-tabpanel-1" />
                <Tab label="Risks & Outlook" id="report-tab-2" aria-controls="report-tabpanel-2" />
                <Tab label="AI Analysis" id="report-tab-3" aria-controls="report-tabpanel-3" icon={<AnalyticsIcon />} iconPosition="start" />
              </Tabs>
            </Box>
            
            <TabPanel value={tabValue} index={0}>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : error ? (
                <Alert 
                  severity="error" 
                  sx={{ my: 2 }}
                  action={
                    <Button color="inherit" size="small" onClick={() => window.location.reload()}>
                      Retry
                    </Button>
                  }
                >
                  {error}
                </Alert>
              ) : (
                <>
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
                </>
              )}
            </TabPanel>
            
            <TabPanel value={tabValue} index={1}>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : error ? (
                <Alert 
                  severity="error" 
                  sx={{ my: 2 }}
                  action={
                    <Button color="inherit" size="small" onClick={() => window.location.reload()}>
                      Retry
                    </Button>
                  }
                >
                  {error}
                </Alert>
              ) : (
                <Grid container spacing={3}>
                  {financialMetrics.length > 0 ? (
                    financialMetrics.map((metric: any, index: number) => (
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
                    ))
                  ) : (
                    <Grid item xs={12}>
                      <Alert severity="info">No financial metrics available.</Alert>
                    </Grid>
                  )}
                </Grid>
              )}
            </TabPanel>
            
            <TabPanel value={tabValue} index={2}>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : error ? (
                <Alert 
                  severity="error" 
                  sx={{ my: 2 }}
                  action={
                    <Button color="inherit" size="small" onClick={() => window.location.reload()}>
                      Retry
                    </Button>
                  }
                >
                  {error}
                </Alert>
              ) : (
                <>
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
                </>
              )}
            </TabPanel>
            
            <TabPanel value={tabValue} index={3}>
              {loadingEnhanced ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', p: 4 }}>
                  <CircularProgress sx={{ mb: 2 }} />
                  <Typography variant="body1" color="text.secondary">
                    Processing enhanced AI analysis...
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    This may take a minute or two.
                  </Typography>
                </Box>
              ) : error ? (
                <Alert 
                  severity="error" 
                  sx={{ my: 2 }}
                  action={
                    <Button color="inherit" size="small" onClick={fetchEnhancedAnalysis}>
                      Retry
                    </Button>
                  }
                >
                  {error}
                </Alert>
              ) : enhancedAnalysis ? (
                <Grid container spacing={3}>
                  {/* AI Insight */}
                  {enhancedAnalysis.insights?.overall && (
                    <Grid item xs={12}>
                      <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
                        <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium', display: 'flex', alignItems: 'center' }}>
                          <AnalyticsIcon sx={{ mr: 1 }} /> AI Insight
                        </Typography>
                        <Typography variant="body1" paragraph sx={{ lineHeight: 1.7, textAlign: 'justify' }}>
                          {enhancedAnalysis.insights.overall}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}
                  
                  {/* Sentiment Analysis */}
                  {enhancedAnalysis.sentiment && (
                    <Grid item xs={12} md={6}>
                      <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 2, height: '100%' }}>
                        <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium', display: 'flex', alignItems: 'center' }}>
                          {enhancedAnalysis.sentiment.sentiment === 'positive' ? (
                            <SentimentSatisfiedAltIcon sx={{ mr: 1 }} />
                          ) : enhancedAnalysis.sentiment.sentiment === 'negative' ? (
                            <SentimentDissatisfiedIcon sx={{ mr: 1 }} />
                          ) : (
                            <SentimentNeutralIcon sx={{ mr: 1 }} />
                          )}
                          Sentiment Analysis
                        </Typography>
                        
                        <Box sx={{ 
                          mb: 3, 
                          p: 2, 
                          borderRadius: 1, 
                          bgcolor: enhancedAnalysis.sentiment.sentiment === 'positive' ? 'success.light' : 
                                  enhancedAnalysis.sentiment.sentiment === 'negative' ? 'error.light' : 'info.light'
                        }}>
                          <Typography variant="h6" sx={{ 
                            color: enhancedAnalysis.sentiment.sentiment === 'positive' ? 'success.dark' : 
                                  enhancedAnalysis.sentiment.sentiment === 'negative' ? 'error.dark' : 'info.dark',
                            display: 'flex',
                            alignItems: 'center'
                          }}>
                            {enhancedAnalysis.sentiment.sentiment === 'positive' ? '😀 Positive' : 
                             enhancedAnalysis.sentiment.sentiment === 'negative' ? '😟 Negative' : '😐 Neutral'}
                            <Box sx={{ ml: 'auto' }}>
                              Score: {Math.round(enhancedAnalysis.sentiment.score * 100)}%
                            </Box>
                          </Typography>
                        </Box>
                        
                        {enhancedAnalysis.insights?.sentiment && (
                          <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
                            {enhancedAnalysis.insights.sentiment}
                          </Typography>
                        )}
                        
                        {enhancedAnalysis.sentiment.distribution && Object.keys(enhancedAnalysis.sentiment.distribution).length > 0 && (
                          <Box sx={{ mt: 3 }}>
                            <Typography variant="subtitle1" gutterBottom>
                              Sentiment Distribution
                            </Typography>
                            <Grid container spacing={1}>
                              {Object.entries(enhancedAnalysis.sentiment.distribution).map(([key, value]: [string, any]) => (
                                <Grid item xs={4} key={key}>
                                  <Box sx={{ 
                                    p: 1, 
                                    textAlign: 'center',
                                    bgcolor: key === 'positive' ? 'success.light' : 
                                            key === 'negative' ? 'error.light' : 'info.light',
                                    borderRadius: 1
                                  }}>
                                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                      {key.charAt(0).toUpperCase() + key.slice(1)}
                                    </Typography>
                                    <Typography variant="h6">
                                      {Math.round(Number(value) * 100)}%
                                    </Typography>
                                  </Box>
                                </Grid>
                              ))}
                            </Grid>
                          </Box>
                        )}
                      </Paper>
                    </Grid>
                  )}
                  
                  {/* Risk Assessment */}
                  {enhancedAnalysis.risk && (
                    <Grid item xs={12} md={6}>
                      <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 2, height: '100%' }}>
                        <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium', display: 'flex', alignItems: 'center' }}>
                          <WarningAmberIcon sx={{ mr: 1 }} /> Risk Assessment
                        </Typography>
                        
                        <Box sx={{ 
                          mb: 3, 
                          p: 2, 
                          borderRadius: 1, 
                          bgcolor: enhancedAnalysis.risk.overall_score > 0.66 ? 'error.light' : 
                                  enhancedAnalysis.risk.overall_score > 0.33 ? 'warning.light' : 'success.light'
                        }}>
                          <Typography variant="h6" sx={{ 
                            color: enhancedAnalysis.risk.overall_score > 0.66 ? 'error.dark' : 
                                  enhancedAnalysis.risk.overall_score > 0.33 ? 'warning.dark' : 'success.dark',
                            display: 'flex',
                            alignItems: 'center'
                          }}>
                            {enhancedAnalysis.risk.overall_score > 0.66 ? 'High Risk' : 
                             enhancedAnalysis.risk.overall_score > 0.33 ? 'Medium Risk' : 'Low Risk'}
                            <Box sx={{ ml: 'auto' }}>
                              Score: {Math.round(enhancedAnalysis.risk.overall_score * 100)}%
                            </Box>
                          </Typography>
                        </Box>
                        
                        {enhancedAnalysis.insights?.risk && (
                          <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 3 }}>
                            {enhancedAnalysis.insights.risk}
                          </Typography>
                        )}
                        
                        {enhancedAnalysis.risk.primary_factors && enhancedAnalysis.risk.primary_factors.length > 0 && (
                          <Box>
                            <Typography variant="subtitle1" gutterBottom>
                              Primary Risk Factors
                            </Typography>
                            <List dense>
                              {enhancedAnalysis.risk.primary_factors.map((factor: string, index: number) => (
                                <React.Fragment key={index}>
                                  <ListItem>
                                    <ListItemText primary={factor} />
                                  </ListItem>
                                  {index < enhancedAnalysis.risk.primary_factors.length - 1 && <Divider component="li" />}
                                </React.Fragment>
                              ))}
                            </List>
                          </Box>
                        )}
                        
                        {enhancedAnalysis.risk.categories && Object.keys(enhancedAnalysis.risk.categories).length > 0 && (
                          <Box sx={{ mt: 3 }}>
                            <Typography variant="subtitle1" gutterBottom>
                              Risk Categories
                            </Typography>
                            <Grid container spacing={1}>
                              {Object.entries(enhancedAnalysis.risk.categories).map(([key, value]: [string, any]) => (
                                <Grid item xs={6} key={key}>
                                  <Box sx={{ 
                                    p: 1, 
                                    textAlign: 'center',
                                    bgcolor: Number(value) > 0.66 ? 'error.light' : 
                                            Number(value) > 0.33 ? 'warning.light' : 'success.light',
                                    borderRadius: 1,
                                    mb: 1
                                  }}>
                                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                      {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                                    </Typography>
                                    <Typography variant="h6">
                                      {Math.round(Number(value) * 100)}%
                                    </Typography>
                                  </Box>
                                </Grid>
                              ))}
                            </Grid>
                          </Box>
                        )}
                      </Paper>
                    </Grid>
                  )}
                  
                  {/* Entities */}
                  {enhancedAnalysis.entities && Object.keys(enhancedAnalysis.entities).length > 0 && (
                    <Grid item xs={12}>
                      <Paper elevation={0} sx={{ p: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
                        <Typography variant="h5" gutterBottom color="primary" sx={{ fontWeight: 'medium', display: 'flex', alignItems: 'center' }}>
                          <BusinessIcon sx={{ mr: 1 }} /> Key Entities
                        </Typography>
                        
                        <Grid container spacing={2}>
                          {Object.entries(enhancedAnalysis.entities).map(([entityType, entities]: [string, any]) => (
                            <Grid item xs={12} md={4} key={entityType}>
                              <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
                                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold', borderBottom: '1px solid', borderColor: 'divider', pb: 1 }}>
                                  {entityType.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                                </Typography>
                                <List dense>
                                  {entities.slice(0, 10).map((entity: any, index: number) => (
                                    <ListItem key={index} sx={{ py: 0.5 }}>
                                      <ListItemText 
                                        primary={entity.text} 
                                        secondary={entity.score ? `Confidence: ${Math.round(entity.score * 100)}%` : null} 
                                      />
                                    </ListItem>
                                  ))}
                                  {entities.length > 10 && (
                                    <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                                      +{entities.length - 10} more
                                    </Typography>
                                  )}
                                </List>
                              </Paper>
                            </Grid>
                          ))}
                        </Grid>
                      </Paper>
                    </Grid>
                  )}
                </Grid>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', p: 4 }}>
                  <Alert severity="info" sx={{ mb: 3, width: '100%' }}>
                    Enhanced AI analysis is not available for this report yet.
                  </Alert>
                  <Button 
                    variant="contained" 
                    startIcon={<AnalyticsIcon />} 
                    onClick={fetchEnhancedAnalysis}
                  >
                    Generate Enhanced Analysis
                  </Button>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    This will use AI to extract entities, analyze sentiment, and assess risks in this report.
                  </Typography>
                </Box>
              )}
            </TabPanel>
          </Paper>
        </Grid>
        
        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Key Metrics
            </Typography>
            {keyMetrics.length > 0 ? (
              <List dense>
                {keyMetrics.map((metric: any, index: number) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemText 
                        primary={metric.name} 
                        secondary={`${metric.value} ${metric.unit}`} 
                        primaryTypographyProps={{ variant: 'subtitle2' }}
                        secondaryTypographyProps={{ variant: 'h6', color: 'primary' }}
                      />
                    </ListItem>
                    {index < keyMetrics.length - 1 && <Divider component="li" />}
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Alert severity="info">No key metrics available.</Alert>
            )}
          </Paper>
          
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Related Reports
            </Typography>
            {relatedReports.length > 0 ? (
              <List dense>
                {relatedReports.slice(0, 5).map((report: any, index: number) => (
                  <React.Fragment key={report.id}>
                    <ListItem 
                      button 
                      component="a" 
                      href={`/reports/${report.id}`}
                    >
                      <ListItemText 
                        primary={`${report.company_name} - ${report.year}`} 
                        secondary={report.processing_status} 
                      />
                    </ListItem>
                    {index < relatedReports.length - 1 && index < 4 && <Divider component="li" />}
                  </React.Fragment>
                ))}
              </List>
            ) : (
              <Alert severity="info">No related reports available.</Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </PageLayout>
  );
} 