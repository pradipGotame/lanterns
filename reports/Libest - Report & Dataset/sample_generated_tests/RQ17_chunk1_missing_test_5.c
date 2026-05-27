/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk1_missing_test_5.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

/*
 * The test harness in the project provides a client context named `ectx`
 * which is initialized in the shared test setup. Declare it extern so
 * this test file can reference it like the exemplar tests do.
 */
extern EST_CTX *ectx;

void rq17_chunk1_missing_test_5(void)
{
    EST_ERROR rv;
    unsigned char *attr_data = NULL;
    int attr_len = 0;

    /* URI that uses .well-known but wrong operation segment -> should be rejected */
    est_client_set_server(ectx, US903_SERVER_IP, US903_TCP_PORT, "/.well-known/foo");
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (attr_data) { free(attr_data); attr_data = NULL; }

    /* URI missing the leading dot in .well-known -> should be rejected */
    est_client_set_server(ectx, US903_SERVER_IP, US903_TCP_PORT, "/well-known/est");
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (attr_data) { free(attr_data); attr_data = NULL; }

    /* Case-variant of segments should be treated distinctly -> expect rejection */
    est_client_set_server(ectx, US903_SERVER_IP, US903_TCP_PORT, "/.WELL-KNOWN/Est");
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (attr_data) { free(attr_data); attr_data = NULL; }

    /* Extra-slash/normalization boundary variant -> verify consistent rejection or non-success
     * (the assertion checks for non-success to detect incorrect acceptance of malformed prefixes)
     */
    est_client_set_server(ectx, US903_SERVER_IP, US903_TCP_PORT, "/.well-known/est//simpleenroll");
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv != EST_ERR_NONE);
    if (attr_data) { free(attr_data); attr_data = NULL; }
}
