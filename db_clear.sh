#!/bin/bash
#
# db_clear.sh - Database clearing utility script
#
# This script provides options to safely clear database tables
# with confirmation prompts and backup options.
#

# Text formatting for better readability
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables - edit these according to your environment
DB_TYPE="sqlite" # Options: sqlite, mysql, postgresql
DB_NAME="backend/annual_reports.db" # For SQLite, this is the file path

# Help function
show_help() {
    echo -e "${BOLD}Database Clearing Utility${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -a, --all         Clear all tables in the database"
    echo "  -t, --table NAME  Clear specific table"
    echo "  -l, --list        List all tables in the database"
    echo "  -b, --backup      Create a backup before clearing"
    echo "  -f, --force       Skip confirmation prompts (use with caution)"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --all --backup     # Backup and clear all tables"
    echo "  $0 --table users      # Clear only the 'users' table"
    echo ""
}

# Create a backup of the database
create_backup() {
    echo -e "${BLUE}Creating database backup...${NC}"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Generate backup filename with timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"
    
    case $DB_TYPE in
        sqlite)
            # SQLite backup
            if [ -f "$DB_NAME" ]; then
                sqlite3 "$DB_NAME" .dump > "$BACKUP_FILE"
                echo -e "${GREEN}Backup created at: $BACKUP_FILE${NC}"
            else
                echo -e "${RED}Error: Database file $DB_NAME not found${NC}"
                exit 1
            fi
            ;;
        mysql)
            # MySQL backup
            mysqldump -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" > "$BACKUP_FILE"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Backup created at: $BACKUP_FILE${NC}"
            else
                echo -e "${RED}Error: Failed to create MySQL backup${NC}"
                exit 1
            fi
            ;;
        postgresql)
            # PostgreSQL backup
            PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Backup created at: $BACKUP_FILE${NC}"
            else
                echo -e "${RED}Error: Failed to create PostgreSQL backup${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Error: Unsupported database type: $DB_TYPE${NC}"
            exit 1
            ;;
    esac
}

# List all tables in the database
list_tables() {
    echo -e "${BLUE}Listing all tables in the database:${NC}"
    
    case $DB_TYPE in
        sqlite)
            sqlite3 "$DB_NAME" ".tables"
            ;;
        mysql)
            mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" -e "SHOW TABLES;" "$DB_NAME"
            ;;
        postgresql)
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "\dt"
            ;;
        *)
            echo -e "${RED}Error: Unsupported database type: $DB_TYPE${NC}"
            exit 1
            ;;
    esac
}

# Get all tables from the database
get_all_tables() {
    case $DB_TYPE in
        sqlite)
            sqlite3 "$DB_NAME" ".tables" | tr ' ' '\n' | grep -v '^$'
            ;;
        mysql)
            mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" -N -e "SHOW TABLES;" "$DB_NAME"
            ;;
        postgresql)
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
            ;;
        *)
            echo -e "${RED}Error: Unsupported database type: $DB_TYPE${NC}"
            exit 1
            ;;
    esac
}

# Clear a specific table
clear_table() {
    local table=$1
    
    echo -e "${YELLOW}Clearing table: $table${NC}"
    
    case $DB_TYPE in
        sqlite)
            sqlite3 "$DB_NAME" "DELETE FROM $table;"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Successfully cleared table: $table${NC}"
            else
                echo -e "${RED}Error: Failed to clear table: $table${NC}"
                return 1
            fi
            ;;
        mysql)
            mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" -e "DELETE FROM $table;" "$DB_NAME"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Successfully cleared table: $table${NC}"
            else
                echo -e "${RED}Error: Failed to clear table: $table${NC}"
                return 1
            fi
            ;;
        postgresql)
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "DELETE FROM $table;"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Successfully cleared table: $table${NC}"
            else
                echo -e "${RED}Error: Failed to clear table: $table${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${RED}Error: Unsupported database type: $DB_TYPE${NC}"
            exit 1
            ;;
    esac
    
    return 0
}

# Clear all tables
clear_all_tables() {
    echo -e "${YELLOW}Clearing all tables in the database...${NC}"
    
    local all_tables=$(get_all_tables)
    local success=true
    
    for table in $all_tables; do
        clear_table "$table"
        if [ $? -ne 0 ]; then
            success=false
        fi
    done
    
    if $success; then
        echo -e "${GREEN}Successfully cleared all tables${NC}"
    else
        echo -e "${RED}There were errors clearing some tables${NC}"
        return 1
    fi
    
    return 0
}

# Initialize variables
CLEAR_ALL=false
SPECIFIC_TABLE=""
CREATE_BACKUP=false
SKIP_CONFIRMATION=false
SHOW_TABLES=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--all)
            CLEAR_ALL=true
            shift
            ;;
        -t|--table)
            SPECIFIC_TABLE="$2"
            shift 2
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        -f|--force)
            SKIP_CONFIRMATION=true
            shift
            ;;
        -l|--list)
            SHOW_TABLES=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Display help if no arguments provided
if [[ $CLEAR_ALL == false && -z $SPECIFIC_TABLE && $SHOW_TABLES == false ]]; then
    show_help
    exit 0
fi

# List tables if requested
if [[ $SHOW_TABLES == true ]]; then
    list_tables
    exit 0
fi

# Create backup if requested
if [[ $CREATE_BACKUP == true ]]; then
    create_backup
fi

# Clearing logic
if [[ $CLEAR_ALL == true ]]; then
    # Confirm before clearing all tables
    if [[ $SKIP_CONFIRMATION == false ]]; then
        echo -e "${RED}${BOLD}WARNING: You are about to clear ALL tables in the database.${NC}"
        echo -e "${RED}${BOLD}This action cannot be undone.${NC}"
        read -p "Are you sure you want to continue? (y/N): " confirm
        if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
            echo -e "${BLUE}Operation cancelled.${NC}"
            exit 0
        fi
    fi
    
    clear_all_tables
elif [[ -n $SPECIFIC_TABLE ]]; then
    # Confirm before clearing specific table
    if [[ $SKIP_CONFIRMATION == false ]]; then
        echo -e "${YELLOW}You are about to clear the table: $SPECIFIC_TABLE${NC}"
        read -p "Are you sure you want to continue? (y/N): " confirm
        if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
            echo -e "${BLUE}Operation cancelled.${NC}"
            exit 0
        fi
    fi
    
    clear_table "$SPECIFIC_TABLE"
fi

echo -e "${GREEN}Database clearing operations completed.${NC}"
exit 0