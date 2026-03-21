# common/config.py

# === 帧参数 ===
FRAME_WIDTH = 1920          
FRAME_HEIGHT = 1080        
BLOCK_SIZE = 8             
FPS = 24                   


GRID_COLS = FRAME_WIDTH // BLOCK_SIZE    # 240
GRID_ROWS = FRAME_HEIGHT // BLOCK_SIZE   # 135


FINDER_SIZE = 7             # Finder Pattern 边长 (块数)
ALIGN_SIZE = 5              # Alignment Pattern 边长 (块数)
SEPARATOR_WIDTH = 1         # 分隔带宽度 (块数)

HEADER_PARITY_BITS = 1
HEADER_FRAME_ID_BITS = 12
HEADER_DATA_LEN_BITS = 16
HEADER_CRC_BITS = 8
HEADER_TOTAL_BITS = 37


SEGMENT_DATA_BITS = 120     # 每段数据位数 (15 字节)
SEGMENT_CRC_BITS = 32       # CRC-32 位数
SEGMENT_TOTAL_BITS = SEGMENT_DATA_BITS + SEGMENT_CRC_BITS  # 152

BLACK_THRESHOLD = 60        # 低于此值判定为黑 (bit=0)
WHITE_THRESHOLD = 195       # 高于此值判定为白 (bit=1)
CONFIDENCE_THRESHOLD = 0.7  # 置信度低于此值标记为不可靠
