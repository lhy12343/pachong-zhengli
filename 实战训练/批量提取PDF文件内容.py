import os
import pdfplumber
from pathlib import Path

def extract_text_from_pdf(pdf_path):
    """
    从单个PDF文件中提取文本内容
    
    Args:
        pdf_path (str): PDF文件路径
        
    Returns:
        str: 提取的文本内容
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"处理文件 {pdf_path} 时出错: {e}")
        return ""

def batch_extract_pdfs(pdf_folder, output_folder=None, max_files=None):
    """
    批量提取PDF文件夹中PDF文件的文本内容
    
    Args:
        pdf_folder (str): 包含PDF文件的文件夹路径
        output_folder (str, optional): 输出文本文件的文件夹路径，默认为None表示不保存到文件
        max_files (int, optional): 最大处理文件数，默认为None表示处理所有文件
        
    Returns:
        dict: 以文件名为键，提取文本为值的字典
    """
    # 创建PDF文件夹路径对象
    pdf_path = Path(pdf_folder)
    
    # 检查PDF文件夹是否存在
    if not pdf_path.exists():
        print(f"错误: 文件夹 {pdf_folder} 不存在")
        return {}
    
    # 获取所有PDF文件
    pdf_files = list(pdf_path.glob("*.pdf"))
    
    # 如果指定了最大文件数，则只处理前max_files个文件
    if max_files is not None:
        pdf_files = pdf_files[:max_files]
    
    print(f"找到 {len(pdf_files)} 个PDF文件，开始处理...")
    
    # 存储提取结果的字典
    extracted_texts = {}
    
    # 批量处理PDF文件
    for i, pdf_file in enumerate(pdf_files):
        print(f"正在处理 ({i+1}/{len(pdf_files)}): {pdf_file.name}")
        text = extract_text_from_pdf(str(pdf_file))
        extracted_texts[pdf_file.name] = text
        
        # 如果指定了输出文件夹，则将文本保存到文件
        if output_folder:
            output_path = Path(output_folder)
            output_path.mkdir(parents=True, exist_ok=True)
            
            txt_filename = pdf_file.stem + ".txt"
            txt_file_path = output_path / txt_filename
            
            try:
                with open(txt_file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"已保存: {txt_file_path}")
            except Exception as e:
                print(f"保存文件 {txt_file_path} 时出错: {e}")
    
    print("处理完成!")
    return extracted_texts

def main():
    """
    主函数 - 演示如何使用批量提取功能
    """
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    
    # 设置PDF文件夹路径为代码文件所在目录中的pdf文件夹
    pdf_folder = current_dir / "pdf"
    
    # 默认输出文件夹路径 (保存提取的文本)
    output_folder = current_dir / "extracted_texts"
    
    # 控制处理的PDF文件数量
    max_files = 2  # 根据要求设置为1进行测试
    
    print("开始批量提取PDF文件内容...")
    print(f"PDF文件夹: {pdf_folder}")
    print(f"最多处理文件数: {max_files}")
    
    # 执行批量提取
    results = batch_extract_pdfs(
        pdf_folder=str(pdf_folder),
        output_folder=str(output_folder),
        max_files=max_files
    )
    
    # 显示完整提取结果
    for filename, text in results.items():
        print(f"\n文件: {filename}")
        print("=" * 50)
        # 输出完整的文本内容
        print(text)
        print("=" * 50)

if __name__ == "__main__":
    main()