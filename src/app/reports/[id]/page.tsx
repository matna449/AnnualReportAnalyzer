'use client';

import React, { useState } from 'react';
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
  ListItemText
} from '@mui/material';
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

// Sample data - in a real app, this would be fetched from an API based on the ID
const sampleReport = {
  id: 1,
  company: 'Apple Inc.',
  ticker: 'AAPL',
  year: '2023',
  uploadDate: 'Feb 26, 2024',
  sector: 'Technology',
  summary: 'Apple Inc. reported strong financial performance in fiscal year 2023, with revenue growth across most product categories and geographic segments. The company continues to invest in innovation and expand its services ecosystem.',
  financials: {
    revenue: '$394.3 billion',
    netIncome: '$96.9 billion',
    eps: '$6.14',
    cashFlow: '$121.2 billion',
    rnd: '$29.9 billion',
  },
  keyMetrics: [
    { name: 'Revenue Growth', value: '8.1%' },
    { name: 'Profit Margin', value: '24.6%' },
    { name: 'Return on Equity', value: '160.2%' },
    { name: 'Debt to Equity', value: '1.52' },
    { name: 'Current Ratio', value: '1.07' },
  ],
  risks: [
    'Global economic conditions and their impact on consumer spending',
    'Supply chain disruptions and manufacturing challenges',
    'Intense competition in all product categories',
    'Regulatory challenges in multiple jurisdictions',
    'Rapid technological changes requiring continuous innovation',
  ],
  outlook: 'The company expects continued growth in its Services segment and stable performance in its hardware business. Apple plans to expand its AI capabilities across its product lineup and invest in emerging technologies.'
};

export default function ReportDetails({ params }: { params: { id: string } }) {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <PageLayout>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {sampleReport.company} ({sampleReport.ticker})
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Annual Report {sampleReport.year} • Uploaded on {sampleReport.uploadDate}
        </Typography>
        <Box sx={{ mt: 1 }}>
          <Chip label={sampleReport.sector} color="primary" size="small" />
        </Box>
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
              </Tabs>
            </Box>
            
            <TabPanel value={tabValue} index={0}>
              <Typography variant="body1" paragraph>
                {sampleReport.summary}
              </Typography>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>
                Key Highlights
              </Typography>
              <List>
                <ListItem>
                  <ListItemText 
                    primary="Strong Services Growth" 
                    secondary="Services revenue reached an all-time high, growing 16.2% year-over-year." 
                  />
                </ListItem>
                <ListItem>
                  <ListItemText 
                    primary="Expanding Product Ecosystem" 
                    secondary="Introduced new products across multiple categories, strengthening the ecosystem." 
                  />
                </ListItem>
                <ListItem>
                  <ListItemText 
                    primary="International Expansion" 
                    secondary="Significant growth in emerging markets, particularly in India and Southeast Asia." 
                  />
                </ListItem>
              </List>
            </TabPanel>
            
            <TabPanel value={tabValue} index={1}>
              <Grid container spacing={3}>
                {Object.entries(sampleReport.financials).map(([key, value]) => (
                  <Grid item xs={12} sm={6} md={4} key={key}>
                    <Card>
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary">
                          {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                        </Typography>
                        <Typography variant="h5" component="div">
                          {value}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </TabPanel>
            
            <TabPanel value={tabValue} index={2}>
              <Typography variant="h6" gutterBottom>
                Risk Factors
              </Typography>
              <List>
                {sampleReport.risks.map((risk, index) => (
                  <ListItem key={index}>
                    <ListItemText primary={risk} />
                  </ListItem>
                ))}
              </List>
              
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="h6" gutterBottom>
                Business Outlook
              </Typography>
              <Typography variant="body1" paragraph>
                {sampleReport.outlook}
              </Typography>
            </TabPanel>
          </Paper>
        </Grid>
        
        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Key Metrics
            </Typography>
            <List dense>
              {sampleReport.keyMetrics.map((metric, index) => (
                <React.Fragment key={index}>
                  <ListItem>
                    <ListItemText 
                      primary={metric.name} 
                      secondary={metric.value} 
                      primaryTypographyProps={{ variant: 'subtitle2' }}
                      secondaryTypographyProps={{ variant: 'h6', color: 'primary' }}
                    />
                  </ListItem>
                  {index < sampleReport.keyMetrics.length - 1 && <Divider component="li" />}
                </React.Fragment>
              ))}
            </List>
          </Paper>
          
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Related Reports
            </Typography>
            <List dense>
              <ListItem button component="a" href="#">
                <ListItemText 
                  primary="Apple Inc. - 2022" 
                  secondary="Previous Year" 
                />
              </ListItem>
              <Divider component="li" />
              <ListItem button component="a" href="#">
                <ListItemText 
                  primary="Microsoft Corporation - 2023" 
                  secondary="Same Sector" 
                />
              </ListItem>
              <Divider component="li" />
              <ListItem button component="a" href="#">
                <ListItemText 
                  primary="Alphabet Inc. - 2023" 
                  secondary="Same Sector" 
                />
              </ListItem>
            </List>
          </Paper>
        </Grid>
      </Grid>
    </PageLayout>
  );
} 