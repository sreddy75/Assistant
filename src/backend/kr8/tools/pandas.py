import base64
import io
from typing import Dict, Any, Optional

from src.backend.kr8.tools import Toolkit
from src.backend.kr8.utils.log import logger
from src.backend.kr8.document import Document
from src.backend.kr8.knowledge.base import AssistantKnowledge

try:
    import pandas as pd
except ImportError:
    raise ImportError("`pandas` not installed. Please install using `pip install pandas`.")


class PandasTools(Toolkit):
    def __init__(self, user_id: Optional[int] = None, knowledge_base: Optional['AssistantKnowledge'] = None):
        super().__init__(name="pandas_tools")
        self.user_id = user_id
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.knowledge_base = knowledge_base
        self.register(self.create_pandas_dataframe)
        self.register(self.run_dataframe_operation)
        self.register(self.load_csv)
        self.register(self.load_excel)
        self.register(self.list_dataframes)

    def load_csv(self, file_name: str, file_content: str) -> str:
        try:
            file_bytes = base64.b64decode(file_content)
            df = pd.read_csv(io.BytesIO(file_bytes))
            df_name = f"df_{file_name.replace('.csv', '').replace(' ', '_')}"
            df_name = f"user_{self.user_id}_{df_name}" if self.user_id else df_name
            self.dataframes[df_name] = df
            logger.info(f"Loaded CSV: {df_name}, shape: {df.shape}")
            
            # Save to pgvector
            self.save_to_pgvector(df_name, df)
            
            return df_name
        except Exception as e:
            logger.error(f"Error loading CSV {file_name}: {str(e)}")
            raise

    def save_to_pgvector(self, df_name: str, df: pd.DataFrame):
        if self.knowledge_base is None:
            logger.error("Knowledge base not available. Cannot save to pgvector.")
            return

        # Convert DataFrame to CSV string representation
        csv_string = df.to_csv(index=False)

        # Create a Document object
        doc = Document(
            content=csv_string,
            name=df_name,
            meta_data={"type": "dataframe", "shape": str(df.shape), "columns": df.columns.tolist()}
        )

        # Save to knowledge base
        try:
            self.knowledge_base.load_document(doc)
            logger.info(f"Saved dataframe {df_name} to pgvector")
        except Exception as e:
            logger.error(f"Error saving dataframe {df_name} to pgvector: {str(e)}")
            logger.exception("Traceback:")
            
    def load_excel(self, file_name: str, file_content: str) -> str:
        try:
            file_bytes = base64.b64decode(file_content)
            df = pd.read_excel(io.BytesIO(file_bytes))
            df_name = f"df_{file_name.replace('.xlsx', '').replace('.xls', '').replace(' ', '_')}"
            df_name = f"user_{self.user_id}_{df_name}" if self.user_id else df_name
            self.dataframes[df_name] = df
            logger.info(f"Loaded Excel: {df_name}, shape: {df.shape}")
            # Save to pgvector
            self.save_to_pgvector(df_name, df)
            return df_name
        except Exception as e:
            logger.error(f"Error loading Excel {file_name}: {str(e)}")
            raise

    def get_dataframe(self, df_name: str) -> Optional[pd.DataFrame]:
        logger.debug(f"Attempting to retrieve dataframe: {df_name}")
        if df_name in self.dataframes:
            logger.debug(f"Found dataframe {df_name} in local memory")
            return self.dataframes[df_name]
        elif self.knowledge_base:
            logger.debug(f"Searching for dataframe {df_name} in knowledge base")
            doc = self.knowledge_base.get_document_by_name(df_name)
            if doc and doc.content:
                try:
                    # Try different encodings
                    encodings = ['utf-8', 'iso-8859-1', 'cp1252', 'latin1']
                    for encoding in encodings:
                        try:
                            df = pd.read_csv(io.StringIO(doc.content), encoding=encoding)
                            self.dataframes[df_name] = df
                            logger.debug(f"Successfully loaded dataframe {df_name} from knowledge base")
                            return df
                        except UnicodeDecodeError:
                            continue
                    else:
                        logger.error(f"Unable to decode the CSV content for {df_name} with any of the tried encodings")
                except Exception as e:
                    logger.error(f"Error loading dataframe from document: {e}")
        logger.warning(f"Dataframe '{df_name}' not found in local memory or knowledge base")
        return None
                
    def list_dataframes(self) -> str:
        if self.user_id:
            user_dfs = {name: df for name, df in self.dataframes.items() if name.startswith(f"user_{self.user_id}_")}
        else:
            user_dfs = self.dataframes
        return "\n".join([f"{name}: {df.shape}" for name, df in user_dfs.items()])

    def create_visualization(self, df_name: str, chart_type: str, x: str, y: str, title: str) -> Dict[str, Any]:
        df = self.get_dataframe(df_name)
        if df is None:
            raise ValueError(f"DataFrame '{df_name}' not found")

        try:
            if chart_type == "line":
                fig = px.line(df, x=x, y=y, title=title)
            elif chart_type == "bar":
                fig = px.bar(df, x=x, y=y, title=title)
            elif chart_type == "scatter":
                fig = px.scatter(df, x=x, y=y, title=title)
            elif chart_type == "histogram":
                fig = px.histogram(df, x=x, title=title)
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")

            return {
                "chart_type": chart_type,
                "data": json.loads(pio.to_json(fig)),
                "interpretation": f"This {chart_type} chart shows the relationship between {x} and {y} in the {df_name} dataset."
            }
        except Exception as e:
            logger.error(f"Error creating visualization: {str(e)}")
            return f"Error creating visualization: {str(e)}"

    def create_pandas_dataframe(
        self, dataframe_name: str, create_using_function: str, function_parameters: Dict[str, Any]
    ) -> str:
        try:
            logger.debug(f"Creating dataframe: {dataframe_name}")
            logger.debug(f"Using function: {create_using_function}")
            logger.debug(f"With parameters: {function_parameters}")

            if dataframe_name in self.dataframes:
                return f"Dataframe already exists: {dataframe_name}"

            # Create the dataframe
            dataframe = getattr(pd, create_using_function)(**function_parameters)
            if dataframe is None:
                return f"Error creating dataframe: {dataframe_name}"
            if not isinstance(dataframe, pd.DataFrame):
                return f"Error creating dataframe: {dataframe_name}"
            if dataframe.empty:
                return f"Dataframe is empty: {dataframe_name}"
            self.dataframes[dataframe_name] = dataframe
            logger.debug(f"Created dataframe: {dataframe_name}")
            return dataframe_name
        except Exception as e:
            logger.error(f"Error creating dataframe: {e}")
            return f"Error creating dataframe: {e}"

    def run_dataframe_operation(self, dataframe_name: str, operation: str, operation_parameters: Dict[str, Any]) -> str:
        try:            
            logger.debug(f"Running operation: {operation}")
            logger.debug(f"On dataframe: {dataframe_name}")
            logger.debug(f"With parameters: {operation_parameters}")

            # Get the dataframe
            dataframe = self.get_dataframe(dataframe_name)
            
            if dataframe is None:
                return f"Error: Dataframe '{dataframe_name}' not found"

            # Run the operation
            result = getattr(dataframe, operation)(**operation_parameters)

            logger.debug(f"Ran operation: {operation}")
            try:
                return result.to_string()
            except AttributeError:
                return str(result)
        except Exception as e:
            logger.error(f"Error running operation: {e}")
            return f"Error running operation: {e}"