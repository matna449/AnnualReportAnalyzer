import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend,
  BarChart,
  Bar
} from 'recharts';

// Sample data - in a real app, this would come from an API
const sampleData = [
  { year: '2019', revenue: 4000, profit: 2400 },
  { year: '2020', revenue: 3000, profit: 1398 },
  { year: '2021', revenue: 5000, profit: 3000 },
  { year: '2022', revenue: 7800, profit: 3908 },
  { year: '2023', revenue: 9000, profit: 4800 },
];

interface FinancialPerformanceChartProps {
  title?: string;
  data: Array<any>;
  dataKeys?: Array<string>;
  xAxisKey?: string;
  colors?: Array<string>;
  chartType?: 'line' | 'bar';
}

const FinancialPerformanceChart: React.FC<FinancialPerformanceChartProps> = ({ 
  title = "Financial Performance Trends",
  data = [],
  dataKeys = ['revenue', 'profit'],
  xAxisKey = 'year',
  colors = ['#8884d8', '#82ca9d'],
  chartType = 'line'
}) => {
  if (data.length === 0) {
    return (
      <Card sx={{ width: '100%', height: '100%', minHeight: 400 }}>
        <CardContent>
          <Typography variant="h6" component="div" gutterBottom>
            {title}
          </Typography>
          <Box sx={{ width: '100%', height: 350, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  // Format the tooltip value based on the data type
  const formatTooltipValue = (value: any) => {
    if (typeof value === 'number') {
      // Check if it's a percentage
      if (value < 100 && dataKeys.some(key => key.toLowerCase().includes('margin') || key.toLowerCase().includes('percentage'))) {
        return `${value.toFixed(2)}%`;
      }
      // Format as currency if it's likely a monetary value
      if (value > 100 || dataKeys.some(key => 
        key.toLowerCase().includes('revenue') || 
        key.toLowerCase().includes('income') || 
        key.toLowerCase().includes('profit') || 
        key.toLowerCase().includes('sales')
      )) {
        return `$${value.toLocaleString()}`;
      }
      // Default number formatting
      return value.toLocaleString();
    }
    return value;
  };

  return (
    <Card sx={{ width: '100%', height: '100%', minHeight: 400 }}>
      <CardContent>
        {title && (
          <Typography variant="h6" component="div" gutterBottom>
            {title}
          </Typography>
        )}
        <Box sx={{ width: '100%', height: 350 }}>
          <ResponsiveContainer width="100%" height="100%">
            {chartType === 'line' ? (
              <LineChart
                data={data}
                margin={{
                  top: 5,
                  right: 30,
                  left: 20,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey={xAxisKey} />
                <YAxis />
                <Tooltip 
                  formatter={(value) => [formatTooltipValue(value), undefined]}
                  labelFormatter={(label) => `${xAxisKey.charAt(0).toUpperCase() + xAxisKey.slice(1)}: ${label}`}
                />
                <Legend />
                {dataKeys.map((key, index) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={colors[index % colors.length]}
                    activeDot={{ r: 8 }}
                    name={key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1')}
                  />
                ))}
              </LineChart>
            ) : (
              <BarChart
                data={data}
                margin={{
                  top: 5,
                  right: 30,
                  left: 20,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey={xAxisKey} />
                <YAxis />
                <Tooltip 
                  formatter={(value) => [formatTooltipValue(value), undefined]}
                  labelFormatter={(label) => `${xAxisKey.charAt(0).toUpperCase() + xAxisKey.slice(1)}: ${label}`}
                />
                <Legend />
                {dataKeys.map((key, index) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    fill={colors[index % colors.length]}
                    name={key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1')}
                  />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

export default FinancialPerformanceChart; 