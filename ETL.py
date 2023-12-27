from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.functions import when
from pyspark.conf import SparkConf
import pyspark.sql.functions as sf
import os 
from pyspark.sql.window import Window

SUBMIT_ARGS = "--packages com.databricks:spark-csv_2.11:1.2.0 pyspark-shell"
os.environ["PYSPARK_SUBMIT_ARGS"] = SUBMIT_ARGS

spark = SparkSession.builder.getOrCreate()

def etl_1_day(path ,file_name):
    df = spark.read.json(path+file_name)
    df = df.select('_source.*')
    df = df.withColumn("Type",
           when((col("AppName") == 'CHANNEL') | (col("AppName") =='DSHD')| (col("AppName") =='KPLUS')| (col("AppName") =='KPlus'), "Truyền Hình")
        .when((col("AppName") == 'VOD') | (col("AppName") =='FIMS_RES')| (col("AppName") =='BHD_RES')| 
              (col("AppName") =='VOD_RES')| (col("AppName") =='FIMS')| (col("AppName") =='BHD')| (col("AppName") =='DANET'), "Phim Truyện")
        .when((col("AppName") == 'RELAX'), "Giải Trí")
        .when((col("AppName") == 'CHILD'), "Thiếu Nhi")
        .when((col("AppName") == 'SPORT'), "Thể Thao")
        .otherwise("Error"))
    df = df.select('Contract','Type','TotalDuration')
    df = df.filter(df.Type != 'Error')
    print('Finished Processing {}'.format(file_name))
    return df

def calculate_most_watch(result1):
    windowspect = Window.partitionBy("Contract").orderBy(sf.desc("TotalDuration"))
    most_watch = result1.withColumn('rank',sf.rank().over(windowspect))
    most_watch = most_watch.filter(most_watch.rank == 1)
    most_watch = most_watch.select("Contract","Type")
    most_watch = most_watch.withColumnRenamed("Type","Most_watch")
    return most_watch

def contract_taste(final):
    final = final.withColumn("Giải Trí",when(sf.col('Giải Trí').isNotNull(),'Relax').otherwise(sf.col('Giải Trí')))
    final = final.withColumn("Phim Truyện",when(sf.col('Phim Truyện').isNotNull(),'Movie').otherwise(sf.col('Phim Truyện')))
    final = final.withColumn("Thiếu Nhi",when(sf.col('Thiếu Nhi').isNotNull(),'Child').otherwise(sf.col('Thiếu Nhi')))
    final = final.withColumn("Thể Thao",when(sf.col('Thể Thao').isNotNull(),'Sport').otherwise(sf.col('Thể Thao')))
    final = final.withColumn("Truyền Hình",when(sf.col('Truyền Hình').isNotNull(),'TV').otherwise(sf.col('Truyền Hình')))
    taste = final.withColumn('Taste',sf.concat_ws('-',*[i for i in final.columns if i != 'Contract']))
    taste = taste.select('Contract','Taste')
    return taste

def main_task():
    path = "E:\\BigData\\Dataset\\log_content\\"
    list_file = os.listdir(path)
    file_name = list_file[0]
    result1 = etl_1_day(path ,file_name)
    for i in list_file[1:]:
        file_name2 = i 
        result2 = etl_1_day(path ,file_name2)
        result1 = result1.union(result2)
        result1 = result1.cache()
    result1 = result1.groupby('Contract','Type').sum()
    result1 = result1.withColumnRenamed('sum(TotalDuration)','TotalDuration')
    most_watch = calculate_most_watch(result1)
    final = result1.groupBy("Contract").pivot("Type").sum("TotalDuration")
    taste = contract_taste(final)
    final = final.join(most_watch,'Contract','inner')
    final = final.join(taste,'Contract','inner')
    print('-----------Saving Data ---------')
    final.repartition(1).write.mode('overwrite').csv(path="E:\\BigData\\SavePath\\",header=True)
    return print('Data Saved Successfully')