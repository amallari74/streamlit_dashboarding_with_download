import pandas as pd
import os
import xlwt
from datetime import datetime
import logging
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_df_as_xls(df, output_file):
    """Save DataFrame directly to XLS format"""
    try:
        wb = xlwt.Workbook()
        ws = wb.add_sheet('Sheet1')
        
        header_style = xlwt.easyxf('font: bold on; align: wrap on')
        
        # Excel column width units are 1/256th of the width of the zero character '0' of the default font
        # Default width = 30 characters * 256 units = 7680 units
        # This provides a reasonable column width that can display about 30 characters without wrapping
        DEFAULT_EXCEL_COLUMN_WIDTH = 7680  # 30 characters * 256 units/character
        
        default_width = DEFAULT_EXCEL_COLUMN_WIDTH
        for j, col in enumerate(df.columns):
            try:
                ws.write(0, j, col, header_style)
                ws.col(j).width = default_width
            except Exception as col_error:
                logger.error(f"Error setting width for column {j} ({col}): {str(col_error)}")
                ws.write(0, j, col, header_style)
        
        for i, row in enumerate(df.values, start=1):
            for j, val in enumerate(row):
                try:
                    if pd.isna(val):
                        ws.write(i, j, '')
                    else:
                        ws.write(i, j, val)
                except Exception as cell_error:
                    logger.error(f"Error writing cell at row {i}, col {j}: {str(cell_error)}")
                    ws.write(i, j, str(val))
        
        wb.save(output_file)
        logger.info(f"Successfully saved file: {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving to XLS: {e}")
        return False

def batch_process_dataframe(df, base_filename, batch_size=1000):
    """
    Process DataFrame into batched XLS files and return them for Streamlit download
    
    Args:
        df (pd.DataFrame): DataFrame to process
        base_filename (str): Base name for the output files
        batch_size (int): Number of rows per file (default 1000)
    
    Returns:
        list: List of tuples (filename, bytes_data) for each batch
    """
    try:
        if df.empty:
            logger.warning("DataFrame is empty, no files will be created")
            return []
            
        files_data = []
        total_rows = len(df)
        batch_size = max(1, batch_size)
        num_batches = (total_rows + batch_size - 1) // batch_size
        
        if total_rows > 0 and num_batches == 0:
            num_batches = 1
        
        logger.info(f"Processing {total_rows} rows into {num_batches} batches")
        
        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, total_rows)
            
            chunk = df.iloc[start_idx:end_idx]
            download_date = datetime.now().strftime('%Y-%m-%d')
            filename = f"{base_filename}_batch{batch_num + 1:03d}_{download_date}.xls"
            
            wb = xlwt.Workbook()
            ws = wb.add_sheet('Sheet1')
            
            header_style = xlwt.easyxf('font: bold on; align: wrap on')
            for j, col in enumerate(chunk.columns):
                ws.write(0, j, col, header_style)
                ws.col(j).width = 7680  # 30 characters * 256
            
            for i, row in enumerate(chunk.values, start=1):
                for j, val in enumerate(row):
                    ws.write(i, j, val if not pd.isna(val) else '')
            
            buffer = io.BytesIO()
            try:
                wb.save(buffer)
                files_data.append((filename, buffer.getvalue()))
            except Exception as e:
                logger.error(f"Failed to save file {filename}: {str(e)}")
                continue
        return files_data

    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        return []
