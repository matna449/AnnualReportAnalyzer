'use client';

import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { SHOW_DEVELOPER_TOOLS } from '@/utils/featureFlags';

interface DebugContainerProps {
  children: React.ReactNode;
  title?: string;
  isVisible?: boolean;
}

/**
 * A container for debugging components that can be conditionally rendered
 * based on feature flags.
 * 
 * @example
 * <DebugContainer title="Metrics Debug Info">
 *   <pre>{JSON.stringify(metrics, null, 2)}</pre>
 * </DebugContainer>
 */
const DebugContainer: React.FC<DebugContainerProps> = ({
  children,
  title = 'Debug Information',
  isVisible = SHOW_DEVELOPER_TOOLS
}) => {
  if (!isVisible) return null;
  
  return (
    <Paper 
      elevation={0}
      sx={{ 
        mt: 2, 
        p: 2, 
        backgroundColor: 'rgba(0, 0, 0, 0.03)',
        border: '1px dashed rgba(0, 0, 0, 0.1)',
        borderRadius: 1
      }}
    >
      <Typography 
        variant="caption" 
        sx={{ 
          display: 'block', 
          color: 'text.secondary',
          fontWeight: 'medium',
          mb: 1
        }}
      >
        🛠️ {title} (Debug Mode)
      </Typography>
      <Box>{children}</Box>
    </Paper>
  );
};

export default DebugContainer; 