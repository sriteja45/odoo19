import logging 
 
from .cache_service import CacheService 
from ..constants import ( 
    POS_PRODUCT_PREFIX, 
    POS_PRODUCT_TTL, 
    DEFAULT_LANGUAGE, 
    LOG_PREFIX 
) 
 
_logger = logging.getLogger(__name__) 
 
 
class PosCache: 
    """ 
    Redis Cache Service for Odoo POS. 
 
    Responsibilities: 
        - Generate Redis Keys 
        - Get Cached POS Products 
        - Cache POS Products 
        - Invalidate POS Product Cache 
    """ 
 
    CACHE_PREFIX = POS_PRODUCT_PREFIX 
 
    DEFAULT_TTL = POS_PRODUCT_TTL 
     
 
 
    def __init__(self): 
        self.cache = CacheService() 
 
    # --------------------------------------------------------- 
    # Cache Key 
    # --------------------------------------------------------- 
 
    def build_key( 
        self, 
        company_id, 
        config_id, 
        pricelist_id=None, 
        lang=DEFAULT_LANGUAGE, 
    ): 
        """ 
        Example: 
 
        pos_products:1:3:1:en_US 
        """ 
 
        return ( 
            f"{self.CACHE_PREFIX}:" 
            f"{company_id}:" 
            f"{config_id}:" 
            f"{pricelist_id or 0}:" 
            f"{lang}" 
        ) 
 
    # --------------------------------------------------------- 
    # GET 
    # --------------------------------------------------------- 
 
    def get_products( 
        self, 
        company_id, 
        config_id, 
        pricelist_id=None, 
        lang=DEFAULT_LANGUAGE, 
    ): 
 
        key = self.build_key( 
            company_id, 
            config_id, 
            pricelist_id, 
            lang, 
        ) 
 
        products = self.cache.get(key) 
 
        if products: 
 
            _logger.info( 
                f"{LOG_PREFIX} HIT : {key}", 
            ) 
 
            return products 
 
        _logger.info( 
            f"{LOG_PREFIX} MISS : {key}", 
        ) 
 
        return None 
 
    # --------------------------------------------------------- 
    # SET 
    # --------------------------------------------------------- 
 
    def set_products( 
        self, 
        company_id, 
        config_id, 
        products, 
        pricelist_id=None, 
        lang=DEFAULT_LANGUAGE, 
        ttl=None, 
    ): 
 
        key = self.build_key( 
            company_id, 
            config_id, 
            pricelist_id, 
            lang, 
        ) 
 
        ttl = ttl or self.DEFAULT_TTL 
 
        self.cache.set( 
            key, 
            products, 
            ttl=ttl, 
        ) 
 
        _logger.info( 
            f"{LOG_PREFIX} SET : {key}", 
        ) 
 
    # --------------------------------------------------------- 
    # DELETE 
    # --------------------------------------------------------- 
 
    def invalidate_products( 
        self, 
        company_id=None, 
    ): 
        """ 
        Invalidate POS Product Cache. 
 
        company_id=None 
 
            Delete all companies 
 
        company_id=1 
 
            Delete only company 1 
        """ 
 
        if company_id: 
 
            pattern = ( 
                f"{self.CACHE_PREFIX}:" 
                f"{company_id}:*" 
            ) 
 
        else: 
 
            pattern = ( 
                f"{self.CACHE_PREFIX}:*" 
            ) 
 
        self.cache.delete_pattern(pattern) 
 
        _logger.info( 
            f"{LOG_PREFIX} INVALIDATE : {pattern}", 
        )